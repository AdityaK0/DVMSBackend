# """
# URL configuration for events app.
# """
# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from apps.events.views import (
#     EventViewSet,
#     FestivalTemplateViewSet,
#     ProductRecommendationViewSet
# )

# # Create router and register viewsets
# router = DefaultRouter()
# router.register(r'', EventViewSet, basename='vendor-events')
# router.register(r'festivals/', FestivalTemplateViewSet, basename='festival-templates')
# router.register(r'recommend-products/', ProductRecommendationViewSet, basename='product-recommendations')

# urlpatterns = [
#     path('', include(router.urls)),
# ]

# apps/events/urls.py

from django.urls import path
from . import views

urlpatterns = [

    # ----------------------------------------------------
    # Event CRUD (same as router: '')
    # ----------------------------------------------------
    path('', views.events_list_create, name='vendor-events-list-create'),   # GET, POST
    path('<int:pk>/', views.event_detail_update_delete, name='vendor-events-detail'),  # GET, PUT, PATCH, DELETE

    # ----------------------------------------------------
    # Event actions (same as /<id>/duplicate/, /publish/, etc)
    # ----------------------------------------------------
    path('<int:pk>/duplicate/', views.event_duplicate, name='vendor-events-duplicate'),
    path('<int:pk>/publish/', views.event_publish, name='vendor-events-publish'),
    path('<int:pk>/poster/generate/', views.event_generate_poster, name='vendor-events-generate-poster'),
    path('<int:pk>/campaign/send/', views.event_campaign_send, name='vendor-events-campaign-send'),

    # ----------------------------------------------------
    # Analytics endpoints
    # ----------------------------------------------------
    path('<int:pk>/analytics/', views.event_analytics, name='vendor-events-analytics'),
    path('<int:pk>/analytics/update/', views.event_analytics_update, name='vendor-events-analytics-update'),

    # ----------------------------------------------------
    # Festival templates (router registered: 'festivals/')
    # ----------------------------------------------------
    path('festivals/', views.festival_templates_list, name='festival-templates-list'),

    # ----------------------------------------------------
    # Product recommendations ('recommend-products/')
    # ----------------------------------------------------
    path('recommend-products/', views.product_recommendations_list, name='product-recommendations'),
]
