from django.contrib import admin
from . import models

auto_register = [
    models.Tax, models.Currency, models.ExchangeRate,
    models.Store, models.Register, models.Role, models.User,
    models.CustomerGroup, models.Customer, models.Address,
    models.Brand, models.Supplier, models.Category,
    models.Product, models.ProductImage, models.VariantAttribute, models.VariantValue,
    models.Inventory, models.InventoryCount, models.InventoryCountItem,
    models.Consignment, models.ConsignmentItem,
    models.PriceBook, models.PriceBookProduct,
    models.Promotion, models.PromotionProduct,
    models.OutletProductTax,
    models.PaymentMethod, models.Sale, models.SaleItem, models.Payment,
    models.SerialNumber,
    models.Cart, models.CartItem, models.Order, models.OrderItem,
    models.LoyaltyAccount, models.LoyaltyTransaction,
    models.GiftCard, models.GiftCardTransaction,
    models.StoreCreditAccount, models.StoreCreditTransaction, models.CustomerAccountTransaction,
    models.AuditLog,
]

for m in auto_register:
    if m not in admin.site._registry:
        admin.site.register(m)