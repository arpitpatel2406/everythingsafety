"""Generic, production-friendly CRUD utilities for Django ORM.

This module provides a comprehensive CRUD (Create, Read, Update, Delete) interface
for Django models with advanced features like audit logging, soft deletes, 
optimistic concurrency control, and bulk operations.

Goals:
    * Provide a thin, explicit abstraction over Django's ORM for common patterns
    * Reduce repetition in views, services, or API endpoints
    * Centralize error handling, audit logging, and transactional guarantees
    * Support pagination, bulk operations, and soft deletes

Design Principles:
    * Explicit over implicit - always pass concrete Model subclasses
    * Return model instances or QuerySets for transparency
    * Fail fast with rich, typed exceptions
    * Optional audit logging with graceful fallbacks
    * Thread-safe design for production environments

Example Usage:
    ```python
    from .models import Product
    from .crud import CRUD
    
    crud = CRUD(Product)
    
    # Create
    product = crud.create({"name": "Test Product", "sku": "TEST-001", "price": 99.99})
    
    # Read
    product = crud.get(pk=1)
    products, pagination = crud.list(filters={"is_active": True}, page=1, page_size=20)
    
    # Update
    product = crud.update(product, {"price": 89.99})
    
    # Delete (soft delete if model supports it)
    crud.delete(product)
    ```

Features:
    * Soft Delete: Automatic detection of 'is_active' or 'deleted_at' fields
    * Optimistic Concurrency: Version checking with 'updated_at' fields
    * Audit Logging: Optional audit trail for all operations
    * Bulk Operations: Efficient bulk create and update operations
    * Thread Safety: Safe for concurrent use in production environments
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import (
    Any, 
    Callable, 
    Dict, 
    Iterable, 
    List, 
    Optional, 
    Sequence, 
    Tuple, 
    Type, 
    TypeVar, 
    Union
)

from django.core.exceptions import (
    ObjectDoesNotExist, 
    MultipleObjectsReturned, 
    ValidationError
)
from django.db import models, transaction
from django.db.models import QuerySet
from django.forms.models import model_to_dict as django_model_to_dict
from django.utils import timezone

# Optional audit logging - graceful fallback if not available
try:
    from .models import AuditLog
    AUDIT_AVAILABLE = True
except ImportError:
    AuditLog = None
    AUDIT_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

# Type definitions
ModelT = TypeVar("ModelT", bound=models.Model)

# Public API exports
__all__ = [
    "CRUD",
    "CRUDConfig", 
    "CRUDException",
    "NotFound",
    "Conflict",
    "ConcurrencyConflict",
    "InvalidData",
    "atomic",
]


# ============================= EXCEPTIONS ====================================

class CRUDException(Exception):
    """Base exception for all CRUD operations.
    
    All CRUD-specific exceptions inherit from this base class,
    making it easy to catch any CRUD-related errors.
    """
    pass


class NotFound(CRUDException):
    """Raised when a requested object cannot be found.
    
    This exception is raised when:
    - get() operations fail to find a matching object
    - Operations reference non-existent primary keys
    """
    pass


class Conflict(CRUDException):
    """Raised when operations conflict with existing data.
    
    This exception is raised when:
    - Unique constraint violations occur
    - Integrity constraints are violated
    - Duplicate key errors happen
    """
    pass


class ConcurrencyConflict(CRUDException):
    """Raised when optimistic concurrency control fails.
    
    This exception is raised when:
    - expected_version doesn't match current version
    - Concurrent modifications are detected
    - Optimistic locking prevents updates
    """
    pass


class InvalidData(CRUDException):
    """Raised when provided data fails validation.
    
    This exception is raised when:
    - Model validation fails
    - Required fields are missing
    - Data types are incorrect
    - Business logic validation fails
    """
    pass


# ============================= CONFIGURATION ====================================

@dataclass(frozen=True)
class CRUDConfig:
    """Configuration options for CRUD operations.
    
    This dataclass controls various aspects of CRUD behavior including
    audit logging, query optimization, and soft delete configuration.
    
    Attributes:
        audit (bool): Enable audit logging for all operations. Default: True
        audit_user_getter (Callable): Function to get current user for audit logs
        default_select_related (Tuple[str, ...]): Relations to auto-select for queries
        default_prefetch_related (Tuple[str, ...]): Relations to auto-prefetch
        soft_delete_field (str): Custom field name for soft delete operations
    
    Example:
        ```python
        config = CRUDConfig(
            audit=True,
            audit_user_getter=lambda: get_current_user(),
            default_select_related=('category', 'brand'),
            soft_delete_field='is_deleted'
        )
        crud = CRUD(Product, config=config)
        ```
    """
    audit: bool = True
    audit_user_getter: Optional[Callable[[], Any]] = None
    default_select_related: Tuple[str, ...] = ()
    default_prefetch_related: Tuple[str, ...] = ()
    soft_delete_field: Optional[str] = None


# ============================= UTILITY FUNCTIONS ====================================

def _model_to_dict(instance: models.Model) -> Dict[str, Any]:
    """Convert a model instance to a dictionary representation.
    
    This function safely serializes a Django model instance to a dictionary,
    excluding many-to-many fields and handling any serialization errors gracefully.
    
    Args:
        instance: The Django model instance to serialize
        
    Returns:
        Dict containing the model's field values
        
    Note:
        This function is used primarily for audit logging and handles
        serialization errors by falling back to manual field extraction.
    """
    try:
        return django_model_to_dict(
            instance, 
            fields=[f.name for f in instance._meta.fields]
        )
    except Exception as e:
        logger.warning(f"Failed to serialize model {instance}: {e}")
        # Fallback: manually extract field values
        data = {}
        for field in instance._meta.fields:
            try:
                data[field.name] = getattr(instance, field.name)
            except Exception:
                data[field.name] = None
        return data


@contextmanager
def atomic(using: str = "default"):
    """Context manager for database transactions.
    
    This is a convenience wrapper around Django's transaction.atomic
    that keeps the import local and provides a clean interface.
    
    Args:
        using: Database alias to use for the transaction
        
    Yields:
        Transaction context
        
    Example:
        ```python
        with atomic():
            # All operations here are wrapped in a transaction
            crud.create(data1)
            crud.update(instance, data2)
        ```
    """
    with transaction.atomic(using=using):
        yield


# ============================= MAIN CRUD CLASS ====================================

class CRUD:
    """Generic CRUD operations for Django models.
    
    This class provides a comprehensive interface for Create, Read, Update, and Delete
    operations on Django models with advanced features like audit logging, soft deletes,
    optimistic concurrency control, and bulk operations.
    
    The class is designed to be thread-safe and can be safely reused across requests.
    All mutating operations are wrapped in database transactions by default.
    
    Attributes:
        model: The Django model class this CRUD instance operates on
        config: Configuration options controlling behavior
        using: Database alias for all operations
    
    Example:
        ```python
        from .models import Product
        crud = CRUD(Product)
        
        # Create a new product
        product = crud.create({
            'name': 'Test Product',
            'sku': 'TEST-001',
            'price': 99.99
        })
        
        # Update the product
        product = crud.update(product, {'price': 89.99})
        
        # List products with pagination
        products, pagination = crud.list(
            filters={'is_active': True},
            page=1,
            page_size=20
        )
        ```
    """

    def __init__(
        self, 
        model: Type[ModelT], 
        *, 
        config: Optional[CRUDConfig] = None, 
        using: str = "default"
    ):
        """Initialize CRUD instance for a specific model.
        
        Args:
            model: Django model class to operate on
            config: Configuration options (uses defaults if not provided)
            using: Database alias to use for all operations
            
        Raises:
            TypeError: If model is not a Django Model subclass
        """
        if not issubclass(model, models.Model):
            raise TypeError("model must be a Django models.Model subclass")
        
        self.model = model
        self.config = config or CRUDConfig()
        self.using = using

    # ============================= CREATE OPERATIONS ====================================
    
    def create(
        self, 
        data: Dict[str, Any], 
        *, 
        commit: bool = True, 
        audit: Optional[bool] = None
    ) -> ModelT:
        """Create a new model instance.
        
        Args:
            data: Dictionary of field values for the new instance
            commit: Whether to save to database immediately
            audit: Override audit logging setting for this operation
            
        Returns:
            The created model instance
            
        Raises:
            InvalidData: If the data fails model validation
            Conflict: If creation violates constraints
        """
        instance = self.model(**data)
        return self._save_instance(
            instance, 
            commit=commit, 
            audit=audit, 
            action="create"
        )

    def bulk_create(
        self,
        objects: Iterable[Union[Dict[str, Any], ModelT]],
        *,
        batch_size: Optional[int] = None,
        ignore_conflicts: bool = False,
        audit: Optional[bool] = None,
    ) -> List[ModelT]:
        """Create multiple model instances efficiently.
        
        Args:
            objects: Iterable of dictionaries or model instances to create
            batch_size: Number of objects to create per database query
            ignore_conflicts: Whether to ignore constraint conflicts
            audit: Override audit logging setting for this operation
            
        Returns:
            List of created model instances
            
        Note:
            This method is more efficient than multiple create() calls
            but may not trigger all Django model signals.
        """
        instances: List[ModelT] = []
        for obj in objects:
            if isinstance(obj, self.model):
                instances.append(obj)
            else:
                instances.append(self.model(**obj))
        
        with atomic(self.using):
            created = self.model.objects.using(self.using).bulk_create(
                instances, 
                batch_size=batch_size, 
                ignore_conflicts=ignore_conflicts
            )
            
            if self._audit_enabled(audit):
                for inst in created:
                    self._write_audit(
                        "create", 
                        inst, 
                        before=None, 
                        after=_model_to_dict(inst)
                    )
            return created

    def upsert(
        self,
        lookup: Dict[str, Any],
        defaults: Dict[str, Any],
        *,
        audit: Optional[bool] = None,
        return_tuple: bool = False,
    ) -> Union[ModelT, Tuple[ModelT, bool]]:
        """Create or update a model instance.
        
        Args:
            lookup: Fields to use for finding existing instance
            defaults: Field values to set on create or update
            audit: Override audit logging setting for this operation
            return_tuple: If True, return (instance, created) tuple
            
        Returns:
            The model instance, or (instance, created) tuple if return_tuple=True
            
        Raises:
            InvalidData: If the data fails model validation
        """
        try:
            with atomic(self.using):
                obj, created = self.model.objects.using(self.using).update_or_create(
                    defaults=defaults, 
                    **lookup
                )
                
                if self._audit_enabled(audit):
                    self._write_audit(
                        "create" if created else "update", 
                        obj, 
                        before=None if created else None, 
                        after=_model_to_dict(obj)
                    )
        except ValidationError as e:
            raise InvalidData(str(e)) from e
        
        return (obj, created) if return_tuple else obj

    # ============================= READ OPERATIONS ====================================
    
    def get(
        self, 
        *, 
        pk: Any = None, 
        audit: Optional[bool] = None, 
        **filters: Any
    ) -> ModelT:
        """Retrieve a single model instance.
        
        Args:
            pk: Primary key value (alternative to using filters)
            audit: Override audit logging setting (currently unused for reads)
            **filters: Additional filter criteria
            
        Returns:
            The model instance matching the criteria
            
        Raises:
            NotFound: If no matching instance is found
            Conflict: If multiple instances match the criteria
        """
        qs = self.model.objects.using(self.using).all()
        
        # Apply default query optimizations
        if self.config.default_select_related:
            qs = qs.select_related(*self.config.default_select_related)
        if self.config.default_prefetch_related:
            qs = qs.prefetch_related(*self.config.default_prefetch_related)
        
        # Build filter criteria
        if pk is not None:
            filters["pk"] = pk
            
        try:
            obj = qs.get(**filters)
            return obj
        except ObjectDoesNotExist as e:
            raise NotFound(f"{self.model.__name__} not found for {filters}") from e
        except MultipleObjectsReturned as e:
            raise Conflict(f"Multiple {self.model.__name__} objects for {filters}") from e

    def list(
        self,
        *,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[Sequence[str]] = None,
        page: Optional[int] = None,
        page_size: int = 50,
        select_related: Sequence[str] = (),
        prefetch_related: Sequence[str] = (),
        values: Optional[Sequence[str]] = None,
        search: Optional[Tuple[str, str]] = None,
    ) -> Tuple[Union[QuerySet, List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
        """List model instances with filtering, pagination, and optimization.
        
        Args:
            filters: Dictionary of filter criteria
            order_by: Sequence of field names for ordering (prefix with '-' for desc)
            page: Page number for pagination (1-based)
            page_size: Number of items per page
            select_related: Relations to select in the same query
            prefetch_related: Relations to prefetch in separate queries  
            values: Field names to return as dicts instead of model instances
            search: Tuple of (field_name, search_term) for text search
            
        Returns:
            Tuple of (queryset/list, pagination_meta)
            
        Note:
            - If values is provided, returns list of dicts instead of QuerySet
            - Pagination meta includes page, page_size, total, and pages count
        """
        qs: QuerySet = self.model.objects.using(self.using).all()
        
        # Apply filters
        if filters:
            qs = qs.filter(**filters)
            
        # Apply search
        if search:
            field, term = search
            qs = qs.filter(**{f"{field}__icontains": term})
        
        # Apply query optimizations
        if self.config.default_select_related:
            qs = qs.select_related(*self.config.default_select_related)
        if select_related:
            qs = qs.select_related(*select_related)
        if self.config.default_prefetch_related:
            qs = qs.prefetch_related(*self.config.default_prefetch_related)
        if prefetch_related:
            qs = qs.prefetch_related(*prefetch_related)
            
        # Apply ordering
        if order_by:
            qs = qs.order_by(*order_by)
        
        # Handle pagination
        pagination_meta: Optional[Dict[str, Any]] = None
        if page is not None:
            if page < 1:
                page = 1
            start = (page - 1) * page_size
            end = start + page_size
            total = qs.count()
            pagination_meta = {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": (total + page_size - 1) // page_size,
            }
            qs = qs[start:end]
        
        # Return values or queryset
        if values:
            return list(qs.values(*values)), pagination_meta
        return qs, pagination_meta

    # ============================= UPDATE OPERATIONS ====================================
    
    def update(
        self,
        instance: ModelT,
        data: Dict[str, Any],
        *,
        partial: bool = True,
        expected_version: Optional[datetime] = None,
        audit: Optional[bool] = None,
        commit: bool = True,
    ) -> ModelT:
        """Update an existing model instance.
        
        Args:
            instance: The model instance to update
            data: Dictionary of field values to update
            partial: Whether to allow partial updates (ignore missing fields)
            expected_version: Expected version for optimistic concurrency control
            audit: Override audit logging setting for this operation
            commit: Whether to save to database immediately
            
        Returns:
            The updated model instance
            
        Raises:
            InvalidData: If the data fails model validation
            ConcurrencyConflict: If expected_version doesn't match current version
        """
        before = _model_to_dict(instance) if self._audit_enabled(audit) else None
        
        # Check optimistic concurrency control
        if expected_version and hasattr(instance, "updated_at"):
            current = getattr(instance, "updated_at")
            if current and expected_version and current != expected_version:
                raise ConcurrencyConflict(
                    f"{self.model.__name__} optimistic lock failed "
                    f"(expected {expected_version}, got {current})."
                )
        
        # Apply field updates
        for k, v in data.items():
            if not partial and not hasattr(instance, k):
                raise InvalidData(f"Field '{k}' not found on {self.model.__name__}")
            setattr(instance, k, v)
        
        return self._save_instance(
            instance, 
            commit=commit, 
            audit=audit, 
            action="update", 
            before=before
        )

    def update_where(
        self,
        filters: Dict[str, Any],
        data: Dict[str, Any],
        *,
        audit: Optional[bool] = None,
        expected_version: Optional[datetime] = None,
    ) -> int:
        """Update multiple instances matching filter criteria.
        
        Args:
            filters: Dictionary of filter criteria to select instances
            data: Dictionary of field values to update
            audit: Override audit logging setting for this operation
            expected_version: Expected version for optimistic concurrency control
            
        Returns:
            Number of instances updated
            
        Raises:
            ConcurrencyConflict: If expected_version is provided and no rows match
            
        Note:
            This method captures before/after state for each updated instance
            when audit logging is enabled, which may impact performance on
            large datasets.
        """
        qs = self.model.objects.using(self.using).filter(**filters)
        
        # Apply optimistic concurrency control
        if expected_version and hasattr(self.model, "updated_at"):
            qs = qs.filter(updated_at=expected_version)
        
        # Capture before state for audit logging
        before_snapshots: List[Tuple[Any, Dict[str, Any]]] = []
        if self._audit_enabled(audit):
            for inst in qs:
                before_snapshots.append((inst.pk, _model_to_dict(inst)))
        
        with atomic(self.using):
            updated = qs.update(**data)
            
            # Write audit entries for updated instances
            if self._audit_enabled(audit) and updated:
                for pk, before in before_snapshots:
                    try:
                        inst = self.model.objects.using(self.using).get(pk=pk)
                        self._write_audit(
                            "update", 
                            inst, 
                            before=before, 
                            after=_model_to_dict(inst)
                        )
                    except self.model.DoesNotExist:
                        # Instance was deleted concurrently
                        continue
        
        if expected_version and updated == 0:
            raise ConcurrencyConflict(
                "No rows updated; optimistic lock failure or filters unmatched"
            )
        
        return updated

    # ============================= DELETE OPERATIONS ====================================
    
    def delete(
        self,
        instance_or_filters: Union[ModelT, Dict[str, Any]],
        *,
        hard: bool = False,
        audit: Optional[bool] = None,
    ) -> int:
        """Delete an instance or instances matching filter criteria.
        
        Args:
            instance_or_filters: Model instance or dictionary of filter criteria
            hard: If True, perform hard delete; otherwise attempt soft delete
            audit: Override audit logging setting for this operation
            
        Returns:
            Number of instances affected (1 for single instance deletion)
            
        Note:
            Soft delete is attempted if the model has 'is_active' (bool) or
            'deleted_at' (datetime) fields, unless hard=True is specified.
        """
        if isinstance(instance_or_filters, self.model):
            # Single instance deletion
            inst = instance_or_filters
            
            if not hard and self._can_soft_delete(inst):
                # Perform soft delete
                before = _model_to_dict(inst) if self._audit_enabled(audit) else None
                self._apply_soft_delete(inst)
                inst.save(
                    using=self.using, 
                    update_fields=self._soft_delete_update_fields(inst)
                )
                
                if self._audit_enabled(audit):
                    self._write_audit(
                        "soft_delete", 
                        inst, 
                        before=before, 
                        after=_model_to_dict(inst)
                    )
                return 1
            
            # Perform hard delete
            before = _model_to_dict(inst) if self._audit_enabled(audit) else None
            count, _ = inst.delete()
            
            if self._audit_enabled(audit):
                self._write_audit("delete", inst, before=before, after={})
            return count
        
        # Multiple instances deletion using filters
        filters = instance_or_filters
        qs = self.model.objects.using(self.using).filter(**filters)
        
        if not hard and self._can_soft_delete(model_instance=None):
            # Perform soft delete on all matching instances
            updated = 0
            for inst in qs:
                before = _model_to_dict(inst) if self._audit_enabled(audit) else None
                self._apply_soft_delete(inst)
                inst.save(
                    using=self.using, 
                    update_fields=self._soft_delete_update_fields(inst)
                )
                
                if self._audit_enabled(audit):
                    self._write_audit(
                        "soft_delete", 
                        inst, 
                        before=before, 
                        after=_model_to_dict(inst)
                    )
                updated += 1
            return updated
        
        # Perform hard delete on all matching instances
        if self._audit_enabled(audit):
            for inst in qs:
                self._write_audit(
                    "delete", 
                    inst, 
                    before=_model_to_dict(inst), 
                    after={}
                )
        
        count, _ = qs.delete()
        return count

    # ============================= INTERNAL HELPER METHODS ====================================
    
    def _save_instance(
        self,
        instance: ModelT,
        *,
        commit: bool,
        audit: Optional[bool],
        action: str,
        before: Optional[Dict[str, Any]] = None,
    ) -> ModelT:
        """Save a model instance with error handling and audit logging.
        
        Args:
            instance: The model instance to save
            commit: Whether to wrap in atomic transaction
            audit: Whether to write audit log entry
            action: Action type for audit logging
            before: Before state for audit logging
            
        Returns:
            The saved model instance
            
        Raises:
            InvalidData: If validation fails
            Conflict: If integrity constraints are violated
        """
        try:
            if commit:
                with atomic(self.using):
                    instance.save(using=self.using)
            else:
                instance.save(using=self.using)
        except ValidationError as e:
            raise InvalidData(str(e)) from e
        except Exception as e:
            # Map common database integrity errors to Conflict exceptions
            error_msg = str(e).lower()
            if "unique" in error_msg or "constraint" in error_msg:
                raise Conflict(str(e)) from e
            raise
        
        if self._audit_enabled(audit):
            self._write_audit(
                action, 
                instance, 
                before=before, 
                after=_model_to_dict(instance)
            )
        
        return instance

    def _audit_enabled(self, audit_flag: Optional[bool]) -> bool:
        """Check if audit logging is enabled for this operation.
        
        Args:
            audit_flag: Override flag for this specific operation
            
        Returns:
            True if audit logging should be performed
        """
        return bool(
            AUDIT_AVAILABLE and 
            (audit_flag if audit_flag is not None else self.config.audit)
        )

    def _write_audit(
        self,
        action: str,
        instance: models.Model,
        *,
        before: Optional[Dict[str, Any]],
        after: Optional[Dict[str, Any]],
    ) -> None:
        """Write an audit log entry for the operation.
        
        Args:
            action: Type of action performed (create, update, delete, etc.)
            instance: The model instance that was modified
            before: State before the operation
            after: State after the operation
            
        Note:
            This method fails silently if audit logging fails to avoid
            disrupting the main operation flow.
        """
        if not AuditLog:
            return
        
        try:
            user = self.config.audit_user_getter() if self.config.audit_user_getter else None
            AuditLog.objects.using(self.using).create(
                user=user if getattr(user, "pk", None) else None,
                action=action,
                entity_type=self.model.__name__,
                entity_id=str(getattr(instance, "pk", "?")),
                before=before,
                after=after,
            )
        except Exception as e:
            # Audit failures should not break the main operation
            logger.warning(f"Audit logging failed: {e}")

    # ============================= SOFT DELETE HELPERS ====================================
    
    def _can_soft_delete(self, model_instance: Optional[models.Model]) -> bool:
        """Check if the model supports soft delete operations.
        
        Args:
            model_instance: Optional model instance (not used currently)
            
        Returns:
            True if soft delete is supported
        """
        field = self._soft_delete_field_name()
        return field is not None

    def _soft_delete_field_name(self) -> Optional[str]:
        """Determine the field name to use for soft delete operations.
        
        Returns:
            Field name for soft delete, or None if not supported
            
        Note:
            Priority order:
            1. Explicitly configured soft_delete_field
            2. 'is_active' boolean field  
            3. 'deleted_at' datetime field
        """
        if self.config.soft_delete_field:
            return (
                self.config.soft_delete_field 
                if hasattr(self.model, self.config.soft_delete_field) 
                else None
            )
        
        # Auto-detect common soft delete patterns
        if hasattr(self.model, "is_active"):
            return "is_active"
        if hasattr(self.model, "deleted_at"):
            return "deleted_at"
        return None

    def _apply_soft_delete(self, instance: models.Model) -> None:
        """Apply soft delete to a model instance.
        
        Args:
            instance: The model instance to soft delete
            
        Note:
            For boolean fields (is_active), sets to False
            For datetime fields (deleted_at), sets to current timestamp
        """
        field = self._soft_delete_field_name()
        if not field:
            return
        
        if field == "is_active":
            setattr(instance, field, False)
        else:  # Assume datetime field
            setattr(instance, field, timezone.now())

    def _soft_delete_update_fields(self, instance: models.Model) -> List[str]:
        """Get the list of fields to update for soft delete operations.
        
        Args:
            instance: The model instance being soft deleted
            
        Returns:
            List of field names to include in the update operation
        """
        field = self._soft_delete_field_name()
        return [field] if field else []
