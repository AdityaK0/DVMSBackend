from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    
    # Customers
    path('customers/', views.get_customers, name='get-customers'),
    path('customers/create/', views.create_customer, name='create-customer'),
    path('customers/<int:customer_id>/update/', views.update_customer, name='update-customer'),
    path('customers/<int:customer_id>/delete/', views.delete_customer, name='delete-customer'),
    

    
    # Dashboard Stats 
    path('products-stats/', views.product_stats, name='dashboard-products-stats'),
    path('customers-stats/', views.customer_stats, name='dashboard-customers-stats'),
    
    # global summary API
    path('summary/', views.dashboard_summary, name='dashboard-summary'),
    
    
    path('invoices/', views.get_invoices, name='get-invoices'),
    path('invoices/<int:invoice_id>/', views.get_invoice_by_id, name='get-invoice'),
    path('invoices/create/', views.create_invoice, name='create-invoice'),
    path("invoices/<int:invoice_id>/update/", views.update_invoice, name="update-invoice"),
    path("invoices/<int:invoice_id>/payments/", views.add_payment, name="add-payment"),
    path("invoices/<int:invoice_id>/history/", views.invoice_history, name="invoice-history"),
    path('invoices/<int:invoice_id>/delete/', views.delete_invoice, name='delete-invoice'),

    # File Upload
    path('invoices/upload/', views.upload_invoices_csv, name='upload-invoices'),
]