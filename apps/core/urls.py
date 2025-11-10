# core/urls.py
from django.urls import path
from .views import get_presigned_url

urlpatterns = [
    path("get_presigned_url/", get_presigned_url, name="get_presigned_url"),
]
