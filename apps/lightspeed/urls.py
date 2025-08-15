from django.urls import path
from . import views

app_name = 'lightspeed'

urlpatterns = [
    # Add your Lightspeed routes here
    path('sales/', views.get_sales, name='get_sales'),
    path('sales/day/', views.get_daily_sales, name='get_daily_sales'),
    path('sales/week/', views.get_weekly_sales, name='get_weekly_sales'),
    path('sales/month/', views.get_monthly_sales, name='get_monthly_sales'),
    path("webhooks/lightspeed/<str:topic>/", views.ls_webhook, name="ls_webhook"),
    path('ensure_webhooks/', views.ensure_webhooks_view, name='ensure_webhooks'),
    path('creditCheck/', views.credit_check, name='credit_check'),
    # path('customers/', views.get_customers, name='get_customers'),
    # path('sync/', views.sync_data, name='sync_data'),
]