from django.urls import path
from . import views

app_name = 'lightspeed'

urlpatterns = [
    # Add your Lightspeed routes here
    path('sales/', views.get_sales, name='get_sales'),
    path('sales/day/', views.get_daily_sales, name='get_daily_sales'),
    path('sales/week/', views.get_weekly_sales, name='get_weekly_sales'),
    path('sales/month/', views.get_monthly_sales, name='get_monthly_sales'),
    # path('customers/', views.get_customers, name='get_customers'),
    # path('sync/', views.sync_data, name='sync_data'),
]