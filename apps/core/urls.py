# core/urls.py
from django.urls import path
from .views import get_task_status

urlpatterns = [
    path("bg-tasks/<int:task_id>/", get_task_status, name="bg_task_status"),
]
