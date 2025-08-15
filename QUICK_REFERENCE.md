# Quick Reference Guide - Database Models

## 🔍 Most Important Models (Start Here)

### Core Business Models
| Model | Purpose | Key Fields |
|-------|---------|------------|
| `Store` | Retail locations | `name`, `address`, `currency_code` |
| `Product` | Items for sale | `name`, `sku`, `price`, `barcode` |
| `Customer` | People who buy | `first_name`, `last_name`, `email` |
| `Sale` | Complete transactions | `total`, `datetime`, `status` |
| `User` | System users/employees | `email`, `role`, `first_name` |

### Transaction Flow
```
1. Product → (scanned) → SaleItem → (grouped) → Sale → (paid) → Payment
2. Sale → (updates) → Inventory → (reduces stock)
3. Customer → (earns) → LoyaltyTransaction → (points)
```

## 📊 Key Relationships to Understand

### Every Sale Has:
- Multiple `SaleItem` records (line items)
- Multiple `Payment` records (cash, card, etc.)
- Tax calculations in `SaleTax`
- Optional customer loyalty points

### Every Store Has:
- Multiple `Register` terminals
- `Inventory` for each product
- Assigned `User` employees
- Default `Tax` rate

### Every Product Has:
- `Inventory` record per store
- Optional `ProductImage` photos
- Optional `VariantValue` (size, color)
- Pricing in `PriceBook` or base `price`

## 🎯 Common Queries You'll Need

### Daily Sales for a Store
```python
today_sales = Sale.objects.filter(
    store=store,
    datetime__date=today,
    status='COMPLETED'
)
total_revenue = sum(sale.total for sale in today_sales)
```

### Product Inventory Check
```python
low_stock = Inventory.objects.filter(
    store=store,
    current_quantity__lt=models.F('reorder_point')
).select_related('product')
```

### Customer Purchase History
```python
customer_sales = Sale.objects.filter(
    customer=customer,
    status='COMPLETED'
).order_by('-datetime')[:10]  # Last 10 purchases
```

### Employee Sales Performance
```python
employee_sales = Sale.objects.filter(
    employee=user,
    datetime__date=today,
    status='COMPLETED'
).aggregate(
    total_sales=models.Sum('total'),
    sale_count=models.Count('id')
)
```

## 🔧 Model Field Patterns

### Every Model Has:
- `id` (UUID primary key)
- Timestamp fields (`created_at`, `updated_at`)
- Soft delete capability (`deleted_at`)

### Money Fields:
All money amounts are stored as `FloatField`:
- `price`, `cost`, `total`, `amount`, etc.
- Consider using `DecimalField` for production (more precise)

### Status Fields:
Most entities have status tracking:
- `Sale.status` → Open, Completed, Refunded, etc.
- `Order.status` → Pending, Paid, Shipped, etc.
- `RegisterShift.status` → Open, Closed

### Foreign Keys:
- `on_delete=models.CASCADE` → Delete child when parent deleted
- `on_delete=models.SET_NULL` → Keep child, set FK to null
- `blank=True, null=True` → Optional relationship

## 🚀 Getting Started Checklist

To understand this database:

1. **Start with Store setup** - Everything revolves around stores
2. **Follow a sale transaction** - Trace from product scan to payment
3. **Understand inventory flow** - How stock moves and updates
4. **Learn customer features** - Loyalty, accounts, order history
5. **Check audit trails** - How changes are tracked

## 📝 Model Categories

### 🏪 **Store Operations** (7 models)
Store, Register, RegisterShift, CashMovement, Tax, Currency, ExchangeRate

### 👥 **People** (6 models)  
User, Role, Customer, CustomerGroup, Address, AuditLog

### 📦 **Products** (9 models)
Product, ProductImage, Category, Brand, Supplier, VariantAttribute, VariantValue, SerialNumber

### 🛒 **Sales** (15 models)
Sale, SaleItem, Payment, SaleTax, SaleAdjustment, SaleAttribute, PaymentExternalAttribute, PaymentSurcharge, SaleItemPromotion, SaleItemSurcharge, SaleItemTaxComponent, EcomCustomCharge, ExternalApplication

### 📊 **Inventory** (5 models)
Inventory, Consignment, ConsignmentItem, InventoryCount, InventoryCountItem

### 💰 **Pricing & Promotions** (4 models)
PriceBook, PriceBookProduct, Promotion, PromotionProduct, OutletProductTax

### 🎁 **Customer Programs** (8 models)
LoyaltyAccount, LoyaltyTransaction, GiftCard, GiftCardTransaction, StoreCreditAccount, StoreCreditTransaction, CustomerAccountTransaction

### 🛒 **E-commerce** (4 models)
Cart, CartItem, Order, OrderItem

**Total: ~60 models** covering complete retail operations

## 💡 Pro Tips

1. **Use the ASCII diagram** - It shows the hierarchy clearly
2. **Follow foreign keys** - They tell the story of relationships
3. **Check Meta classes** - They define indexes and constraints
4. **Look for calculated properties** - Sale model has `@property` methods
5. **Understand soft deletes** - Most records aren't actually deleted
6. **Use select_related()** - For better query performance
7. **Check unique constraints** - They prevent duplicate data
