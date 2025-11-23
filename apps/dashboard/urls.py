from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Dashboard Stats
    # path('stats/', views.dashboard_stats, name='dashboard-stats'),
    path('summary/', views.dashboard_summary, name='dashboard-summary'),
    
    # Activity
    path('activity/', views.recent_activity, name='recent-activity'),
    path('activity/<int:activity_id>/', views.delete_activity, name='delete-activity'),
    
    # Events
    # path('events/', views.get_events, name='get-events'),
    # path('events/create/', views.create_event, name='create-event'),
    
    # Customers
    path('customers/', views.get_customers, name='get-customers'),
    path('customers/create/', views.create_customer, name='create-customer'),
    path('customers/<int:customer_id>/update/', views.update_customer, name='update-customer'),
    path('customers/<int:customer_id>/delete/', views.delete_customer, name='delete-customer'),
    

    
    
    # Messages
    path('messages/send/', views.send_message, name='send-message'),
    
    
    # Dashboard Stats 
    path('products-stats/', views.product_stats, name='dashboard-products-stats'),
    path('customers-stats/', views.customer_stats, name='dashboard-customers-stats'),
    # path('recent-activities/', views.recent_activities, name='dashboard-recent-activities'),
    
    # Optional unified summary API
    path('summary/', views.dashboard_summary, name='dashboard-summary'),
    
    
    path('invoices/', views.get_invoices, name='get-invoices'),
    path('invoices/<int:invoice_id>/', views.get_invoice_by_id, name='get-invoice'),
    path('invoices/create/', views.create_invoice, name='create-invoice'),
    path("invoices/<int:invoice_id>/update/", views.update_invoice, name="update-invoice"),
    path("invoices/<int:invoice_id>/history/", views.invoice_history, name="invoice-history"),
    path('invoices/<int:invoice_id>/delete/', views.delete_invoice, name='delete-invoice'),

    # File Upload
    path('invoices/upload/', views.upload_invoices_csv, name='upload-invoices'),
]