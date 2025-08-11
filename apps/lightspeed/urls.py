from django.urls import path
from . import views

app_name = 'lightspeed'

urlpatterns = [
    # Add your Lightspeed routes here
    path('sales/', views.get_sales, name='get_sales'),
    # path('customers/', views.get_customers, name='get_customers'),
    # path('sync/', views.sync_data, name='sync_data'),
]