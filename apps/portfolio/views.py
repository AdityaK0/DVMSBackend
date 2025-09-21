# apps/portfolio/views.py

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta, datetime
import json

from .models import (
    Portfolio, PortfolioSection, PortfolioCollection, 
    PortfolioTestimonial, PortfolioContactInquiry, 
    PortfolioAnalytics, PortfolioTheme
)
from .serializers import (
    PortfolioSerializer, PublicPortfolioSerializer, 
    PortfolioCreateSerializer, PortfolioUpdateSerializer,
    PortfolioSectionSerializer, PortfolioCollectionSerializer,
    PortfolioTestimonialSerializer, PortfolioContactInquirySerializer,
    PortfolioThemeSerializer, PortfolioAnalyticsSerializer,
    PortfolioProductSerializer
)
from apps.products.models import Product
from apps.vendors.models import Vendor


# ============ PUBLIC VIEWS ============

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_portfolio_view(request, slug):
    """
    Public portfolio view by slug
    URL: /api/portfolio/public/{slug}/
    """
    try:
        portfolio = get_object_or_404(
            Portfolio,
            slug=slug,
            is_public=True,
            vendor__is_active=True
        )
        
        # Track view (simple implementation)
        portfolio.view_count += 1
        portfolio.last_viewed = timezone.now()
        portfolio.save(update_fields=['view_count', 'last_viewed'])
        
        # Update daily analytics
        today = timezone.now().date()
        analytics, created = PortfolioAnalytics.objects.get_or_create(
            portfolio=portfolio,
            date=today,
            defaults={'page_views': 1, 'unique_visitors': 1}
        )
        if not created:
            analytics.page_views += 1
            analytics.save(update_fields=['page_views'])
        
        serializer = PublicPortfolioSerializer(portfolio)
        return Response(serializer.data)
        
    except Portfolio.DoesNotExist:
        return Response(
            {'error': 'Portfolio not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_portfolio_products(request, slug):
    """
    Get products from portfolio with filtering
    URL: /api/portfolio/public/{slug}/products/
    """
    portfolio = get_object_or_404(
        Portfolio,
        slug=slug,
        is_public=True,
        vendor__is_active=True
    )
    
    products = portfolio.get_all_products()
    
    # Apply filters
    category = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    search = request.GET.get('search')
    featured_only = request.GET.get('featured')
    
    if category:
        products = products.filter(category__name__iexact=category)
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass
    if search:
        products = products.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) |
            Q(category__name__icontains=search)
        )
    if featured_only == 'true':
        products = products.filter(is_featured=True)
    
    # Pagination
    page_size = min(int(request.GET.get('page_size', 12)), 50)
    page = int(request.GET.get('page', 1))
    start = (page - 1) * page_size
    end = start + page_size
    
    total_count = products.count()
    products_page = products[start:end]
    
    serializer = PortfolioProductSerializer(products_page, many=True)
    
    # Get available categories for filtering
    # categories = portfolio.vendor.products.filter(
    #     is_active=True, 
    #     category__isnull=False
    # ).values_list('category