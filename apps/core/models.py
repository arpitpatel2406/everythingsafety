"""
====================================================================================
                    RETAIL POINT OF SALE (POS) DATABASE SCHEMA
====================================================================================

This file defines the complete database structure for a comprehensive retail 
management system supporting:
• Multi-store operations with individual registers
• Complete sales transaction processing
• Inventory management and stock transfers
• Customer loyalty and account management
• E-commerce integration
• Comprehensive audit trail

For detailed documentation, see:
• DATABASE_OVERVIEW.md - Business logic explanation
• DATABASE_ERD.md - Visual relationship diagrams

====================================================================================
                            ENTITY RELATIONSHIP TREE
====================================================================================

Legend: 
├─< = "has many" (one-to-many relationship)
└─< = "has many" (last item in list)
─< = "has many" (simple relationship)

Tax (VAT/Sales Tax definitions)
 ├─< Store (default_tax) ...................... Retail locations
 │    ├─< Register ............................. POS terminals/cash registers
 │    │    ├─< RegisterShift ................... Employee work sessions
 │    │    │    └─< CashMovement ............... Cash drawer transactions
 │    │    └─< Payment ......................... Transaction payments
 │    ├─< Inventory (Product) .................. Stock levels per store
 │    ├─< Consignment (from_store/to_store) .... Stock transfers between stores
 │    │    └─< ConsignmentItem (Product) ....... Individual items in transfer
 │    ├─< PriceBook ............................ Special pricing rules
 │    │    └─< PriceBookProduct (Product) ...... Products with special pricing
 │    ├─< Promotion ............................ Discount campaigns
 │    │    └─< PromotionProduct (Product) ...... Products eligible for discounts
 │    ├─< OutletProductTax (Product, Tax) ...... Store-specific tax overrides
 │    └─< Sale ................................. Complete transactions
 │         ├─< SaleItem ........................ Individual line items
 │         │    ├─< Product .................... Items being sold
 │         │    │    ├─< ProductImage .......... Product photos
 │         │    │    ├─< VariantValue .......... Size, color, etc.
 │         │    │    │    └─< VariantAttribute . Size, color definitions
 │         │    │    ├─< Inventory ............. Stock tracking
 │         │    │    ├─< ConsignmentItem ....... Transfer tracking
 │         │    │    ├─< PriceBookProduct ...... Special pricing
 │         │    │    └─< PromotionProduct ...... Promotion eligibility
 │         │    ├─< Salesperson (User) ......... Commission tracking
 │         │    ├─< SerialNumber ............... Individual item tracking
 │         │    ├─< SaleItemPromotion (Promotion) Applied discounts
 │         │    ├─< SaleItemSurcharge .......... Additional fees per item
 │         │    └─< SaleItemTaxComponent ....... Tax breakdown per item
 │         ├─< Payment .......................... Payment methods & amounts
 │         │    ├─< PaymentExternalAttribute ... Card/external payment details
 │         │    └─< PaymentSurcharge ........... Payment processing fees
 │         ├─< SaleTax .......................... Tax summary for transaction
 │         ├─< SaleAdjustment .................. Manual price adjustments
 │         ├─< SaleAttribute ................... Additional sale metadata
 │         ├─< EcomCustomCharge ................ Shipping, handling fees
 │         ├─< ExternalApplication ............. Third-party app integration
 │         ├─< LoyaltyTransaction .............. Points earned/redeemed
 │         ├─< GiftCardTransaction ............. Gift card usage
 │         ├─< StoreCreditTransaction .......... Store credit usage
 │         └─< CustomerAccountTransaction ...... Account billing

Currency (USD, EUR, etc.)
 ├─< Store (currency_code) .................... Store's base currency
 ├─< Sale (currency_code) ..................... Transaction currency
 └─< ExchangeRate (base_currency, quote_currency) Currency conversion rates

Role (Admin, Manager, Staff, Cashier)
 └─< User ...................................... System users/employees
      ├─< RegisterShift ........................ Employee work sessions
      ├─< Sale (employee) ...................... Sales attribution
      └─< AuditLog ............................. Change tracking

CustomerGroup (VIP, Regular, Wholesale, etc.)
 └─< Customer .................................. People who make purchases
      ├─< Address .............................. Shipping/billing addresses
      ├─< Order ................................ E-commerce orders
      │    ├─< OrderItem (Product) ............. Items in orders
      │    ├─ Shipping Address ................. Order delivery address
      │    └─ Billing Address .................. Order payment address
      ├─< Sale ................................. In-store purchases
      ├─< LoyaltyAccount ....................... Points program membership
      │    └─< LoyaltyTransaction .............. Points activity
      ├─< StoreCreditAccount ................... Store credit balance
      │    └─< StoreCreditTransaction .......... Store credit activity
      └─< CustomerAccountTransaction ........... Account billing activity

LoyaltyAccount ─< LoyaltyTransaction ........... Points program activity
GiftCard ─< GiftCardTransaction ................ Gift card usage tracking
StoreCreditAccount ─< StoreCreditTransaction ... Store credit activity

Cart ............................................. Shopping cart sessions
 └─< CartItem (Product) ........................ Items in cart

InventoryCount ................................... Stock counting/auditing
 └─< InventoryCountItem (Product) ............... Individual count records

AuditLog ......................................... Change tracking for compliance
                                                 (tracks all entity modifications)

====================================================================================
                               BUSINESS FLOW SUMMARY
====================================================================================

1. SETUP: Create Stores → Registers → Users (employees) → Products → Tax rates
2. SALES: Customer brings products → Employee scans items → System calculates 
          taxes/discounts → Customer pays → Receipt printed → Inventory updated
3. INVENTORY: Receive stock → Create consignments → Update inventory levels
4. CUSTOMERS: Track purchases → Award loyalty points → Manage store credit
5. REPORTING: Audit all transactions → Generate sales reports → Track performance

Total Models: ~40 business entities + ~15 relationship tables + ~8 enums = 60+ classes
File Size: 800+ lines of well-structured Django models with comprehensive relationships

"""

# SQLAlchemy version removed; Django ORM models below.
from __future__ import annotations
import uuid
from django.db import models
from django.utils import timezone

# ===============================================================================
#                           ENUMS & CHOICE DEFINITIONS
# ===============================================================================
# These define the allowed values for various status and type fields throughout
# the system. They ensure data consistency and provide readable options.
class ItemType(models.TextChoices):
    SIMPLE = "simple", "Simple"
    VARIANT = "variant", "Variant"
    MATRIX = "matrix", "Matrix"
    NON_INVENTORY = "non_inventory", "Non Inventory"

class AddressType(models.TextChoices):
    BILLING = "billing", "Billing"
    SHIPPING = "shipping", "Shipping"
    OTHER = "other", "Other"

class SaleStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    COMPLETED = "COMPLETED", "Completed"
    REFUNDED = "REFUNDED", "Refunded"
    VOIDED = "VOIDED", "Voided"
    ONACCOUNT = "ONACCOUNT", "On Account"
    LAYAWAY = "LAYAWAY", "Layaway"
    CLOSED = "CLOSED", "Closed"
    SAVED = "SAVED", "Saved"

class SaleState(models.TextChoices):
    PENDING = "pending", "Pending"
    CLOSED = "closed", "Closed"
    PARKED = "parked", "Parked"

class SaleSource(models.TextChoices):
    USER = "USER", "User"
    API = "API", "API"
    IMPORT = "IMPORT", "Import"
    ECOM = "ECOM", "E-Commerce"

class LineStatus(models.TextChoices):
    NORMAL = "normal", "Normal"
    RETURNED = "returned", "Returned"
    CANCELLED = "cancelled", "Cancelled"
    FULFILLED = "fulfilled", "Fulfilled"
    BACKORDERED = "backordered", "Backordered"

class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    PROCESSING = "processing", "Processing"
    SHIPPED = "shipped", "Shipped"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"
    REFUNDED = "refunded", "Refunded"

class ConsignmentType(models.TextChoices):
    SUPPLIER = "SUPPLIER", "Supplier"
    OUTLET = "OUTLET", "Outlet"
    STOCKTAKE = "STOCKTAKE", "Stocktake"
    RETURN = "RETURN", "Return"

class ShiftStatus(models.TextChoices):
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"

# ===============================================================================
#                    CORE BUSINESS ENTITIES: TAXES, CURRENCY, STORES
# ===============================================================================
# These are the foundational models that everything else builds upon.
# Every retail system needs stores, tax rates, and currency definitions.
class Tax(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)
    display_name = models.CharField(max_length=120, blank=True, null=True)
    rate = models.FloatField()
    is_default = models.BooleanField(default=False)

class Currency(models.Model):
    code = models.CharField(max_length=3, primary_key=True)
    symbol = models.CharField(max_length=8, blank=True, null=True)

class ExchangeRate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    base_currency = models.ForeignKey(Currency, related_name="base_rates", on_delete=models.CASCADE)
    quote_currency = models.ForeignKey(Currency, related_name="quote_rates", on_delete=models.CASCADE)
    rate = models.FloatField()
    as_of = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["base_currency", "quote_currency"], name="uq_exchange_pair")]

class Store(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, blank=True, null=True, unique=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    timezone = models.CharField(max_length=64, blank=True, null=True)
    currency_code = models.ForeignKey(Currency, blank=True, null=True, on_delete=models.SET_NULL)
    currency_symbol = models.CharField(max_length=8, blank=True, null=True)
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=120, blank=True, null=True)
    state = models.CharField(max_length=120, blank=True, null=True)
    postal_code = models.CharField(max_length=32, blank=True, null=True)
    country = models.CharField(max_length=120, blank=True, null=True)
    default_tax = models.ForeignKey(Tax, blank=True, null=True, on_delete=models.SET_NULL)
    is_online = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["name"])]

class Register(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True, null=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    receipt_prefix = models.CharField(max_length=20, blank=True, null=True)
    receipt_sequence = models.IntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["store", "code"], name="uq_registers_store_code")]

class Role(models.Model):
    # Admin, Manager, Staff, Cashier, TestUser.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)

class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=120, blank=True, null=True)
    last_name = models.CharField(max_length=120, blank=True, null=True)
    email = models.EmailField(max_length=255, unique=True)
    username = models.CharField(max_length=120, unique=True, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    password_hash = models.CharField(max_length=255, blank=True, null=True)
    enabled = models.BooleanField(default=True)
    role = models.ForeignKey(Role, blank=True, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["first_name", "last_name"])]

class RegisterShift(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    register = models.ForeignKey(Register, on_delete=models.CASCADE)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=16, choices=ShiftStatus.choices, default=ShiftStatus.OPEN)
    opening_float = models.FloatField(default=0.0)
    closing_amount = models.FloatField(blank=True, null=True)
    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["register", "opened_at"])]

class CashMovement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shift = models.ForeignKey(RegisterShift, on_delete=models.CASCADE)
    amount = models.FloatField()
    reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["shift"])]

# ---------------- Customers & Addresses ----------------
class CustomerGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)

class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_code = models.CharField(max_length=120, unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=120, blank=True, null=True)
    last_name = models.CharField(max_length=120, blank=True, null=True)
    email = models.EmailField(max_length=255, unique=True, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    mobile = models.CharField(max_length=50, blank=True, null=True)
    password_hash = models.CharField(max_length=255, blank=True, null=True)
    group = models.ForeignKey(CustomerGroup, blank=True, null=True, on_delete=models.SET_NULL)
    loyalty_points = models.IntegerField(default=0)
    account_balance = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["first_name", "last_name"])]

class Address(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, blank=True, null=True, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=AddressType.choices, blank=True, null=True)
    line1 = models.CharField(max_length=255)
    line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=120, blank=True, null=True)
    postal_code = models.CharField(max_length=32)
    country = models.CharField(max_length=120)

# ---------------- Suppliers / Brands / Categories ----------------
class Brand(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)

class Supplier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    contact_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=120, blank=True, null=True)
    state = models.CharField(max_length=120, blank=True, null=True)
    postal_code = models.CharField(max_length=32, blank=True, null=True)
    country = models.CharField(max_length=120, blank=True, null=True)

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey("self", blank=True, null=True, on_delete=models.CASCADE)
    path = models.CharField(max_length=1024, blank=True, null=True)
    level = models.IntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["name"])]
        constraints = [models.UniqueConstraint(fields=["parent", "name"], name="uq_categories_parent_name")]

# ---------------- Products ----------------
class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=120, unique=True)
    barcode = models.CharField(max_length=120, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    price = models.FloatField()
    cost = models.FloatField(blank=True, null=True)
    price_includes_tax = models.BooleanField(default=False)
    tax = models.ForeignKey(Tax, blank=True, null=True, on_delete=models.SET_NULL)
    category = models.ForeignKey(Category, blank=True, null=True, on_delete=models.SET_NULL)
    brand = models.ForeignKey(Brand, blank=True, null=True, on_delete=models.SET_NULL)
    supplier = models.ForeignKey(Supplier, blank=True, null=True, on_delete=models.SET_NULL)
    item_type = models.CharField(max_length=20, choices=ItemType.choices, default=ItemType.SIMPLE)
    parent_product = models.ForeignKey("self", blank=True, null=True, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    is_published_online = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["name"]), models.Index(fields=["barcode"])]

class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image_url = models.TextField()
    sort_order = models.IntegerField(default=0)

class VariantAttribute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)

class VariantValue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    attribute = models.ForeignKey(VariantAttribute, on_delete=models.CASCADE)
    value = models.CharField(max_length=120)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["product", "attribute"], name="uq_variant_values_product_attribute")]

# ---------------- Inventory ----------------
class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    current_quantity = models.IntegerField(default=0)
    reorder_point = models.IntegerField(blank=True, null=True)
    reorder_amount = models.IntegerField(blank=True, null=True)
    average_cost = models.FloatField(blank=True, null=True)
    last_counted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ("product", "store")
        indexes = [models.Index(fields=["store"])]

class InventoryCount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=32, default="IN_PROGRESS")

    class Meta:
        indexes = [models.Index(fields=["store"])]

class InventoryCountItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    count = models.ForeignKey(InventoryCount, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    expected_qty = models.IntegerField(default=0)
    counted_qty = models.IntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["count", "product"], name="uq_inventory_count_item")]

# ---------------- Consignments ----------------
class Consignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=20, choices=ConsignmentType.choices)
    from_store = models.ForeignKey(Store, related_name="consignments_from", blank=True, null=True, on_delete=models.SET_NULL)
    to_store = models.ForeignKey(Store, related_name="consignments_to", blank=True, null=True, on_delete=models.SET_NULL)
    supplier = models.ForeignKey(Supplier, blank=True, null=True, on_delete=models.SET_NULL)
    reference = models.CharField(max_length=120, blank=True, null=True)
    status = models.CharField(max_length=32, default="OPEN")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["type", "status"])]

class ConsignmentItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consignment = models.ForeignKey(Consignment, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    cost = models.FloatField(blank=True, null=True)

# ---------------- Price Books & Promotions ----------------
class PriceBook(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    starts_at = models.DateTimeField(blank=True, null=True)
    ends_at = models.DateTimeField(blank=True, null=True)
    outlet = models.ForeignKey(Store, blank=True, null=True, on_delete=models.CASCADE)
    customer_group = models.ForeignKey(CustomerGroup, blank=True, null=True, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["is_active", "starts_at", "ends_at"])]

class PriceBookProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    price_book = models.ForeignKey(PriceBook, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    retail_price = models.FloatField(blank=True, null=True)
    loyalty_amount = models.FloatField(blank=True, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["price_book", "product"], name="uq_pricebook_product")]

class Promotion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    starts_at = models.DateTimeField(blank=True, null=True)
    ends_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    outlet = models.ForeignKey(Store, blank=True, null=True, on_delete=models.CASCADE)
    customer_group = models.ForeignKey(CustomerGroup, blank=True, null=True, on_delete=models.CASCADE)
    discount_percent = models.FloatField(blank=True, null=True)
    discount_amount = models.FloatField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["is_active", "starts_at", "ends_at"])]

class PromotionProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["promotion", "product"], name="uq_promotion_product")]

class OutletProductTax(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    tax = models.ForeignKey(Tax, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["store", "product"], name="uq_outlet_product_tax")]

# ---------------- Sales ----------------
class PaymentMethod(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)
    ledger_code = models.CharField(max_length=64, blank=True, null=True)

class Sale(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    register = models.ForeignKey(Register, on_delete=models.CASCADE)
    employee = models.ForeignKey(User, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, blank=True, null=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=16, choices=SaleStatus.choices, default=SaleStatus.COMPLETED)
    state = models.CharField(max_length=16, choices=SaleState.choices, blank=True, null=True)
    source = models.CharField(max_length=32, choices=SaleSource.choices, default=SaleSource.USER)
    source_id = models.CharField(max_length=255, blank=True, null=True)
    complete_open_sequence_id = models.UUIDField(blank=True, null=True)
    accounts_transaction_id = models.UUIDField(blank=True, null=True)
    has_unsynced_on_account_payments = models.BooleanField(blank=True, null=True)
    invoice_number = models.CharField(max_length=64, unique=True, blank=True, null=True)
    receipt_number = models.CharField(max_length=64, blank=True, null=True)
    short_code = models.CharField(max_length=32, blank=True, null=True)
    return_ids = models.JSONField(default=list, blank=True)
    currency_code = models.ForeignKey(Currency, blank=True, null=True, on_delete=models.SET_NULL)
    exchange_rate_used = models.FloatField(blank=True, null=True)
    datetime = models.DateTimeField(default=timezone.now)
    sale_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    return_for = models.ForeignKey("self", blank=True, null=True, on_delete=models.SET_NULL)
    is_refund = models.BooleanField(default=False)
    version = models.BigIntegerField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["store", "datetime"])]
    
    @property
    def subtotal(self):
        """Calculate subtotal from line items."""
        return sum(item.total_price for item in self.saleitem_set.all())
    
    @property
    def total_discount(self):
        """Calculate total discount from line items."""
        return sum(item.total_discount for item in self.saleitem_set.all())
    
    @property
    def total_tax(self):
        """Calculate total tax from line items."""
        return sum(item.total_tax for item in self.saleitem_set.all())
    
    @property
    def total_loyalty(self):
        """Calculate total loyalty from line items."""
        return sum(item.total_loyalty_value for item in self.saleitem_set.all())
    
    @property
    def total_surcharge(self):
        """Calculate total surcharge from payments."""
        return sum(
            surcharge.amount 
            for payment in self.payment_set.all() 
            for surcharge in payment.surcharges.all()
        )
    
    @property
    def total(self):
        """Calculate final total (subtotal - discount + tax + surcharge)."""
        return self.subtotal - self.total_discount + self.total_tax + self.total_surcharge
    
    @property
    def total_price_incl(self):
        """Calculate total including tax."""
        return self.subtotal + self.total_tax

class SaleItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    salesperson = models.ForeignKey(User, related_name="sale_items", blank=True, null=True, on_delete=models.SET_NULL)
    tax = models.ForeignKey(Tax, blank=True, null=True, on_delete=models.SET_NULL)
    quantity = models.IntegerField()
    unit_price = models.FloatField()
    price = models.FloatField()
    price_total = models.FloatField()
    discount_amount = models.FloatField(default=0.0)
    discount = models.FloatField(default=0.0)
    total_discount = models.FloatField(default=0.0)
    unit_discount = models.FloatField(default=0.0)
    tax_amount = models.FloatField(default=0.0)
    tax_total = models.FloatField(default=0.0)
    unit_tax = models.FloatField(default=0.0)
    cost = models.FloatField(blank=True, null=True)
    cost_total = models.FloatField(blank=True, null=True)
    unit_cost = models.FloatField(blank=True, null=True)
    total_cost = models.FloatField(blank=True, null=True)
    total_price = models.FloatField()
    total_tax = models.FloatField(default=0.0)
    loyalty_value = models.FloatField(default=0.0)
    unit_loyalty_value = models.FloatField(default=0.0)
    total_loyalty_value = models.FloatField(default=0.0)
    status = models.CharField(max_length=16, choices=LineStatus.choices, default=LineStatus.NORMAL)
    note = models.TextField(blank=True, null=True)
    return_reason = models.CharField(max_length=255, blank=True, null=True)
    price_set = models.BooleanField(default=False)
    sequence = models.IntegerField(default=0)
    gift_card_number = models.CharField(max_length=255, blank=True, null=True)
    is_return = models.BooleanField(default=False)
    serial_number = models.ForeignKey("SerialNumber", blank=True, null=True, on_delete=models.SET_NULL)

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, blank=True, null=True, on_delete=models.CASCADE)
    order = models.ForeignKey("Order", blank=True, null=True, on_delete=models.CASCADE)
    register = models.ForeignKey(Register, blank=True, null=True, on_delete=models.CASCADE)
    register_open_sequence_id = models.UUIDField(blank=True, null=True)
    retailer_payment_type_id = models.UUIDField(blank=True, null=True)
    payment_type_id = models.CharField(max_length=64, blank=True, null=True)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True, null=True)
    amount = models.FloatField()
    datetime = models.DateTimeField(default=timezone.now)
    payment_date = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    external_ref = models.CharField(max_length=255, blank=True, null=True)
    source_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["datetime"])]

# ---------------- Sales Tax Components ----------------
class SaleTax(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, related_name="sale_taxes", on_delete=models.CASCADE)
    tax = models.ForeignKey(Tax, on_delete=models.CASCADE)
    amount = models.FloatField()

class SaleItemTaxComponent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale_item = models.ForeignKey(SaleItem, related_name="tax_components", on_delete=models.CASCADE)
    rate_id = models.UUIDField()
    total_tax = models.FloatField()

# ---------------- Sale Adjustments ----------------
class SaleAdjustment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, related_name="sale_adjustments", on_delete=models.CASCADE)
    type = models.CharField(max_length=64)
    amount = models.FloatField()
    reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

# ---------------- External Applications ----------------
class ExternalApplication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, related_name="external_apps", on_delete=models.CASCADE)
    application_id = models.CharField(max_length=255)
    external_id = models.CharField(max_length=255)
    version = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

# ---------------- Sale Attributes ----------------
class SaleAttribute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, related_name="sale_attributes", on_delete=models.CASCADE)
    attribute = models.CharField(max_length=128)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["sale", "attribute"], name="uq_sale_attribute")]

# ---------------- Payment External Attributes ----------------
class PaymentExternalAttribute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, related_name="external_attributes", on_delete=models.CASCADE)
    source = models.CharField(max_length=128)
    card_last_four_digits = models.CharField(max_length=4, blank=True, null=True)
    card_last_four = models.CharField(max_length=4, blank=True, null=True)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    card_brand = models.CharField(max_length=64, blank=True, null=True)

# ---------------- Sale Item Promotions & Surcharges ----------------
class SaleItemPromotion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale_item = models.ForeignKey(SaleItem, related_name="item_promotions", on_delete=models.CASCADE)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE)
    discount_amount = models.FloatField()

class SaleItemSurcharge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale_item = models.ForeignKey(SaleItem, related_name="item_surcharges", on_delete=models.CASCADE)
    type = models.CharField(max_length=64)
    amount = models.FloatField()
    name = models.CharField(max_length=255, blank=True, null=True)

# ---------------- Payment Surcharge ----------------
class PaymentSurcharge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, related_name="surcharges", on_delete=models.CASCADE)
    type = models.CharField(max_length=64)
    amount = models.FloatField()
    name = models.CharField(max_length=255, blank=True, null=True)

# ---------------- E-commerce Custom Charges ----------------
class EcomCustomCharge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, related_name="ecom_charges", on_delete=models.CASCADE)
    type = models.CharField(max_length=64)
    amount = models.FloatField()
    tax_amount = models.FloatField(default=0.0)
    amount_incl = models.FloatField()
    name = models.CharField(max_length=255, blank=True, null=True)

# ---------------- Serial Numbers ----------------
class SerialNumber(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    code = models.CharField(max_length=255, unique=True)
    is_sold = models.BooleanField(default=False)
    sale_item = models.ForeignKey(SaleItem, blank=True, null=True, on_delete=models.SET_NULL)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["product"])]

# ---------------- Cart & Orders ----------------
class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, blank=True, null=True, on_delete=models.CASCADE)

class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["cart", "product"], name="uq_cart_items_cart_product")]

class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, blank=True, null=True, on_delete=models.SET_NULL)
    location = models.ForeignKey(Store, on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    shipping_address = models.ForeignKey(Address, related_name="+", blank=True, null=True, on_delete=models.SET_NULL)
    billing_address = models.ForeignKey(Address, related_name="+", blank=True, null=True, on_delete=models.SET_NULL)
    shipping_method = models.CharField(max_length=120, blank=True, null=True)
    shipping_fee = models.FloatField(default=0.0)
    shipping_tax = models.FloatField(default=0.0)
    subtotal = models.FloatField(default=0.0)
    total_discount = models.FloatField(default=0.0)
    total_tax = models.FloatField(default=0.0)
    total = models.FloatField(default=0.0)
    order_date = models.DateTimeField(default=timezone.now)
    tracking_number = models.CharField(max_length=255, blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["location", "order_date"])]

class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.FloatField()
    discount_amount = models.FloatField(default=0.0)
    tax_amount = models.FloatField(default=0.0)
    cost = models.FloatField(blank=True, null=True)
    total_price = models.FloatField()
    total_tax = models.FloatField(default=0.0)
    status = models.CharField(max_length=16, choices=LineStatus.choices, default=LineStatus.NORMAL)
    note = models.TextField(blank=True, null=True)

# ---------------- Loyalty ----------------
class LoyaltyAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE)
    balance = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

class LoyaltyTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(LoyaltyAccount, on_delete=models.CASCADE)
    sale = models.ForeignKey(Sale, blank=True, null=True, on_delete=models.SET_NULL)
    amount = models.FloatField()
    reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["account"])]

# ---------------- Gift Cards ----------------
class GiftCard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, unique=True)
    initial_balance = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

class GiftCardTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gift_card = models.ForeignKey(GiftCard, on_delete=models.CASCADE)
    sale = models.ForeignKey(Sale, blank=True, null=True, on_delete=models.SET_NULL)
    type = models.CharField(max_length=32)
    amount = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["gift_card"])]

# ---------------- Store Credit & Customer Account ----------------
class StoreCreditAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE)
    balance = models.FloatField(default=0.0)

class StoreCreditTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(StoreCreditAccount, on_delete=models.CASCADE)
    sale = models.ForeignKey(Sale, blank=True, null=True, on_delete=models.SET_NULL)
    amount = models.FloatField()
    reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

class CustomerAccountTransaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    sale = models.ForeignKey(Sale, blank=True, null=True, on_delete=models.SET_NULL)
    amount = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)
    note = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["customer"])]

# ---------------- Audit ----------------
class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=120)
    entity_type = models.CharField(max_length=120)
    entity_id = models.CharField(max_length=64)
    before = models.TextField(blank=True, null=True)
    after = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["created_at"]),
        ]