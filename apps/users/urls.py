from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserRegistrationView, UserLoginView, UserProfileView,user_profile_update_fbv,logout,
    AddressListCreateView, AddressDetailView
)
from . import telegram_views
from . import auth_views

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', auth_views.user_login_view, name='user-login'),
    path('login/otp/request/', auth_views.request_otp_view, name='request-otp'),
    path('login/otp/verify/', auth_views.verify_otp_login_view, name='verify-otp'),
    path('logout/', logout, name='user-logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('profile/<int:pk>/',user_profile_update_fbv, name='user-profile-update'),
    path('addresses/', AddressListCreateView.as_view(), name='address-list-create'),
    path('addresses/<int:pk>/', AddressDetailView.as_view(), name='address-detail'),
    path("telegram/link/", telegram_views.generate_telegram_link),
    path("telegram/webhook/", telegram_views.telegram_webhook),
    path("request_otp/", telegram_views.request_otp),
    path("verify_otp/", telegram_views.verify_otp),
    
]


# urls.py configuration
"""
from django.urls import path
from . import views

urlpatterns = [
    path('api/login/', views.user_login_view, name='user-login'),
    path('api/login/otp/request/', views.request_otp_view, name='request-otp'),
    path('api/login/otp/verify/', views.verify_otp_login_view, name='verify-otp'),
]
"""


# /api/telegram/link → creates signed deep-link for vendor

# /api/telegram/webhook → handles /start <token> from Telegram


# {
#   "message": {
#     "chat": {"id": 987654321},
#     "text": "/start vendor_abc123"
#   }
# }
