# Database Structure Overview

## System Purpose
This is a comprehensive Point of Sale (POS) and Retail Management System that handles:
- **Sales Processing**: Complete transaction management
- **Inventory Management**: Stock tracking and control
- **Customer Management**: Customer data and loyalty programs
- **Multi-store Operations**: Support for multiple retail locations
- **E-commerce Integration**: Online and offline sales

## Core Business Entities

### 🏪 **Store Management**
- **Store**: Individual retail locations
- **Register**: Cash registers/POS terminals within stores
- **RegisterShift**: Work sessions by employees
- **CashMovement**: Cash drawer transactions

### 👥 **People & Roles**
- **User**: System users (employees, managers, etc.)
- **Role**: Permission levels (Admin, Manager, Staff, Cashier)
- **Customer**: People who make purchases
- **CustomerGroup**: Customer categorization for pricing/promotions

### 📦 **Product Catalog**
- **Product**: Items for sale
- **Category**: Product organization hierarchy
- **Brand**: Product manufacturers/brands
- **Supplier**: Product suppliers
- **VariantAttribute/VariantValue**: Product variations (size, color, etc.)

### 💰 **Pricing & Promotions**
- **Tax**: Tax rates and calculations
- **PriceBook**: Special pricing for customer groups/stores
- **Promotion**: Discounts and special offers
- **Currency**: Multi-currency support

### 📊 **Inventory Management**
- **Inventory**: Stock levels per store
- **Consignment**: Stock transfers between stores
- **InventoryCount**: Stock counting/auditing
- **SerialNumber**: Tracking individual items

### 🛒 **Sales & Transactions**
- **Sale**: Complete transaction records
- **SaleItem**: Individual products within a sale
- **Payment**: Payment methods and amounts
- **Order**: E-commerce/special orders

### 🎁 **Customer Programs**
- **LoyaltyAccount**: Customer loyalty points
- **GiftCard**: Gift card management
- **StoreCreditAccount**: Store credit system

### 📋 **System Management**
- **AuditLog**: Change tracking for security/compliance

## Key Relationships

### Central Hub: **Store**
Everything revolves around stores:
```
Store → Registers → Sales → SaleItems → Products
Store → Inventory (stock levels)
Store → Consignments (transfers)
Store → Users (employees)
```

### Transaction Flow:
```
Customer → Sale → SaleItems → Products
Sale → Payments
Sale → Taxes
Sale → Promotions/Discounts
```

### Product Hierarchy:
```
Category → Products → Variants
Products → Inventory (per store)
Products → PriceBooks (special pricing)
Products → Promotions
```

## Data Flow Examples

### 🛍️ **Making a Sale:**
1. Customer brings products to register
2. Employee scans products (creates SaleItems)
3. System calculates taxes, discounts, loyalty points
4. Customer pays (creates Payment records)
5. Inventory is automatically reduced
6. Receipt generated with sale number

### 📦 **Receiving Inventory:**
1. Supplier delivers products
2. Create Consignment record
3. Add ConsignmentItems for each product
4. Update Inventory quantities
5. Record costs and serial numbers

### 🎯 **Running Promotions:**
1. Create Promotion with dates and rules
2. Link to specific products or categories
3. System automatically applies during sales
4. Track promotion effectiveness

## Technical Notes

- **UUIDs**: All primary keys use UUID for uniqueness across systems
- **Soft Deletes**: Many models use `deleted_at` instead of hard deletes
- **Timestamps**: Comprehensive tracking of when records are created/modified
- **JSON Fields**: Flexible data storage for complex attributes
- **Indexing**: Strategic database indexes for performance
- **Multi-currency**: Full support for international operations

## Quick Reference: Model Count
- **Core Models**: ~40 main business entities
- **Relationship Models**: ~15 linking tables
- **Enum Classes**: ~8 choice definitions
- **Total Lines**: ~800+ lines of well-structured Django models

This system can handle everything from a single store to a large multi-location retail chain with e-commerce integration.
