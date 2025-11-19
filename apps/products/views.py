from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Prefetch
from .models import Product, Category, ProductImage
from .serializers import ProductSerializer, ProductListSerializer, CategorySerializer
from ..utils.upload_image import upload_product_images,delete_product_images
from django.db import connection
from .service import get_vendor_products_combined, get_filtered_products
import cloudinary.uploader



import logging
logger = logging.getLogger(__name__)


# Product List with filters (Public)
@api_view(['GET'])
@permission_classes([AllowAny])
def product_list(request):
    """List all active products with filtering, search, and pagination"""
    # FIXED: Start with optimized queryset to avoid N+1 (vendor, category, images)
    products = (
        Product.objects.filter(is_active=True, is_archived=False)
        .select_related('vendor', 'category')
        .prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.only('id', 'github_image_url', 'image', 'is_primary'), to_attr='images_prefetched')
        )
    )
    
    # Apply filters
    category = request.GET.get('category')
    vendor = request.GET.get('vendor')
    is_featured = request.GET.get('is_featured')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    in_stock = request.GET.get('in_stock')
    search = request.GET.get('search')
    
    if category:
        products = products.filter(category_id=category)
    if vendor:
        products = products.filter(vendor_id=vendor)
    if is_featured:
        products = products.filter(is_featured=is_featured.lower() == 'true')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    if in_stock and in_stock.lower() == 'true':
        products = products.filter(stock_quantity__gt=0)
    if search:
        products = products.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search) | 
            Q(sku__icontains=search)
        )
    
    # Ordering
    ordering = request.GET.get('ordering', '-created_at')
    if ordering in ['name', '-name', 'price', '-price', 'created_at', '-created_at']:
        products = products.order_by(ordering)
    
    # Pagination
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 20)
    
    paginator = Paginator(products, page_size)
    page_obj = paginator.get_page(page)
    
    serializer = ProductListSerializer(
        page_obj.object_list, 
        many=True, 
        context={'request': request}
    )
    
    return Response({
        'results': serializer.data,
        'count': paginator.count,
        'total_pages': paginator.num_pages,
        'current_page': int(page),
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    })


# Product Detail (Public)
@api_view(['GET'])
@permission_classes([AllowAny])
def product_detail(request, pk):
    """Get product details"""
    try:
        # FIXED: Restrict to active, non-archived and optimize relations
        product = (
            Product.objects.select_related('vendor', 'category')
            .prefetch_related(
                Prefetch('images', queryset=ProductImage.objects.only('id', 'github_image_url', 'image', 'is_primary'))
            )
            .get(pk=pk, is_active=True, is_archived=False)
        )
        
    except Product.DoesNotExist:
        return Response(
            {"detail": "Product not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = ProductSerializer(product, context={'request': request})
    return Response(serializer.data)




# views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import Product, Category
from .serializers import ProductSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_product(request):
    """Create a new product (text data only)."""
    if not hasattr(request.user, 'vendor'):
        return Response(
            {"error": "Only vendors can create products"},
            status=status.HTTP_403_FORBIDDEN
        )

    vendor = request.user.vendor
    data = request.data
    category_id = data.get('category')
    if not category_id:
        return Response({"category": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        category = Category.objects.get(id=category_id, is_active=True)
    except Category.DoesNotExist:
        return Response({"category": "Invalid category selected."}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ProductSerializer(data=data, context={'request': request})
    if serializer.is_valid():
        with transaction.atomic():
            image_urls = data.get('image_urls') or data.getlist('image_urls[]') or []
            sizes = data.get('sizes') or data.getlist('sizes[]') or []
            

            # Normalize the data to a clean list
            if isinstance(image_urls, str):
                import json
                try:
                    image_urls = json.loads(image_urls)
                except Exception:
                    image_urls = [image_urls]
            elif not isinstance(image_urls, (list, tuple)):
                image_urls = [image_urls]

            product = serializer.save(
                vendor=vendor,
                category=category,
                image_urls=image_urls,
                primary_image=image_urls[0] if image_urls else None,
                sizes=sizes
            )

        response_serializer = ProductSerializer(product, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Create Product (Vendor only) - Commented out legacy code removed

# Update Product - Commented out legacy code removed

from .serializers import ProductUpdateSerializer
from .service import sync_featured_product

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_product(request, pk):
    """Update product; image updates handled manually."""
    
    try:
        product = Product.objects.get(pk=pk, vendor__user=request.user)
    except Product.DoesNotExist:
        return Response({"detail": "Product not found"}, status=404)

    # Update normal fields (no image updates here)
    serializer = ProductUpdateSerializer(
        product,
        data=request.data,
        partial=True
    )
    serializer.is_valid(raise_exception=True)
    updated_product = serializer.save()

    # -----------------------
    # IMAGE HANDLING
    # -----------------------
    
    existing = updated_product.image_urls or []
    
    # Safely get lists even if sent as single values
    images_to_delete = request.data.get("images_to_delete", [])
    if isinstance(images_to_delete, str):
        images_to_delete = [images_to_delete]
        
    new_urls = request.data.get("image_urls", [])
    if isinstance(new_urls, str):
        new_urls = [new_urls]

    # Use sets for O(1) lookups and deduplication
    delete_set = set(images_to_delete)
    existing_set = set(existing)
    
    # Remove deleted images
    final_urls = [url for url in existing if url not in delete_set]

    # Add new S3 URLs (avoid duplicates)
    current_final_set = set(final_urls)
    for url in new_urls:
        if url and url not in current_final_set:
            final_urls.append(url)
            current_final_set.add(url)

    updated_product.image_urls = final_urls
    updated_product.primary_image = final_urls[0] if final_urls else None
    updated_product.save()
    sync_featured_product(updated_product)
    return Response(ProductUpdateSerializer(updated_product).data)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
# @parser_classes([MultiPartParser, FormParser])
def activate_product(request, pk):
    """Update a product"""
    
    try:
        product = Product.objects.get(pk=pk, vendor__user=request.user)
    except Product.DoesNotExist:
        return Response(
            {"detail": "Product not found or you don't have permission"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    product.is_active = True
    product.save(update_fields=["is_active"])
    
    return Response(
            {"detail": "Product activated successfully"}, 
            status=status.HTTP_200_OK
            
        )


# Delete Product (Vendor only - soft delete)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product(request, pk):
    """Soft delete a product"""
    
    try:
        product = Product.objects.get(pk=pk, vendor__user=request.user)
    except Product.DoesNotExist:
        return Response(
            {"detail": "Product not found or you don't have permission"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Soft delete
    product.is_archived = True
    product.save(update_fields=["is_archived"])
    
    return Response(status=status.HTTP_204_NO_CONTENT)


# apps/products/api.py


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_products(request):
    """Get all products for the current vendor"""

    if not hasattr(request.user, 'vendor'):
        return Response(
            {"error": "Only vendors can access this endpoint"},
            status=status.HTTP_403_FORBIDDEN
        )

    vendor = request.user.vendor
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))
    query = request.GET.get('q',"").strip()

    # data = get_vendor_products_data(vendor, request=request, page=page, page_size=page_size)
    data = get_vendor_products_combined(
        vendor,
        request=None,
        page=page,
        page_size=page_size,
        query=query,
        include_private=False,
    )
        
    return Response(data)

# Vendor's Products (Dashboard) - Commented out legacy code removed


# Vendor Catalog (Public - specific vendor's products)
@api_view(['GET'])
@permission_classes([AllowAny])
def vendor_catalog(request, vendor_id):
    """Get all active products for a specific vendor"""
    # FIXED: Optimize queryset (vendor, category, images)
    products = (
        Product.objects.filter(
            vendor_id=vendor_id,
            is_active=True,
            stock_quantity__gt=0
        )
        .select_related('vendor', 'category')
        .prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.only('id', 'github_image_url', 'image', 'is_primary'), to_attr='images_prefetched')
        )
        .order_by('-created_at')
    )
    
    # Pagination
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 20)
    
    paginator = Paginator(products, page_size)
    page_obj = paginator.get_page(page)
    
    serializer = ProductListSerializer(
        page_obj.object_list, 
        many=True, 
        context={'request': request}
    )
    
    return Response({
        'results': serializer.data,
        'count': paginator.count,
        'total_pages': paginator.num_pages,
        'current_page': int(page),
    })


# Categories
@api_view(['GET'])
@permission_classes([AllowAny])
def category_list(request):
    """List all active categories"""
    categories = Category.objects.filter(is_active=True).only('id', 'name', 'is_default', 'vendor_id')
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)





# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def search_products(request):
#     """Optimized: Search products for the current vendor"""
    
#     user = request.user
#     vendor = getattr(user, "vendor", None)
#     if not vendor:
#         return Response(
#             {"error": "Only vendors can access this endpoint"},
#             status=status.HTTP_403_FORBIDDEN
#         )

#     query = request.GET.get("q", "").strip()
    
#     try:
#         page = int(request.GET.get("page", 1))
#     except (TypeError, ValueError):
#         page = 1

#     try:
#         page_size = int(request.GET.get("page_size", 10))
#     except (TypeError, ValueError):
#         page_size = 10
        
#     data = get_search_products(vendor, request=request,query=query,page=page, page_size=page_size)
    
#     return Response(data)
    
    
    
    # products_qs = (
    #     Product.objects.filter(vendor=vendor, is_active=True, is_archived=False)
    #     .select_related("vendor", "category")
    #     .prefetch_related(
    #         Prefetch(
    #             "images",
    #             queryset=ProductImage.objects.all(),
    #             to_attr="images_prefetched"
    #         )
    #     )
    # )

    # if query:
    #     products_qs = products_qs.filter(
    #         Q(name__icontains=query)
    #         | Q(description__icontains=query)
    #         | Q(sku__icontains=query)
    #     )

    # # Pagination handling (safe + integer conversion)
    # try:
    #     page = int(request.GET.get("page", 1))
    # except (TypeError, ValueError):
    #     page = 1

    # try:
    #     page_size = int(request.GET.get("page_size", 10))
    # except (TypeError, ValueError):
    #     page_size = 10

    # paginator = Paginator(products_qs.order_by("-created_at"), page_size)
    # page_obj = paginator.get_page(page)

    # serializer = ProductListSerializer(
    #     page_obj.object_list,
    #     many=True,
    #     context={"request": request}
    # )

    # return Response({
    #     "results": serializer.data,
    #     "count": paginator.count,
    #     "total_pages": paginator.num_pages,
    #     "current_page": page,
    #     "has_next": page_obj.has_next(),
    #     "has_previous": page_obj.has_previous(),
    # })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def filter_products(request):
    """Filter products for the current vendor"""
    if not hasattr(request.user, 'vendor'):
        return Response(
            {"error": "Only vendors can access this endpoint"},
            status=status.HTTP_403_FORBIDDEN
        )

    vendor = request.user.vendor
    data = get_filtered_products(vendor, request.GET, request=request)
    return Response(data)


# @api_view(["GET"])
# @permission_classes([IsAuthenticated])
# def filter_products(request):
#     """Filter products for the current vendor"""
#     if not hasattr(request.user, 'vendor'):
#         return Response(
#             {"error": "Only vendors can access this endpoint"},
#             status=status.HTTP_403_FORBIDDEN
#         )

#     vendor = request.user.vendor
#     products = Product.objects.filter(vendor=vendor,is_archived=False)

#     # Get filters
#     is_active = request.GET.get("is_active")
#     category = request.GET.get("category") or None
#     min_price = request.GET.get("min_price") or None
#     max_price = request.GET.get("max_price") or None
#     # Apply filters
#     if is_active is not None:
#         products = products.filter(is_active=is_active.lower() == "true")

#     if category:
#         products = products.filter(category__iexact=category)

#     if min_price:
#         try:
#             min_price = float(min_price)
#             products = products.filter(price__gte=min_price)
#         except ValueError:
#             pass  # ignore invalid numbers

#     if max_price:
#         try:
#             max_price = float(max_price)
#             products = products.filter(price__lte=max_price)
#         except ValueError:
#             pass

#     # Pagination
#     page = request.GET.get("page", 1)
#     page_size = request.GET.get("page_size", 10)
#     paginator = Paginator(products, page_size)
#     page_obj = paginator.get_page(page)

#     serializer = ProductListSerializer(
#         page_obj.object_list,
#         many=True,
#         context={'request': request}
#     )

#     return Response({
#         "results": serializer.data,
#         "count": paginator.count,
#         "total_pages": paginator.num_pages,
#         "current_page": int(page),
#         "has_next": page_obj.has_next(),
#         "has_previous": page_obj.has_previous(),
#     })




@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def vendor_categories(request):
    if request.method == "GET":
        # FIXED: Guard vendor
        if not hasattr(request.user, 'vendor'):
            return Response({"error": "Only vendors can access this endpoint"}, status=status.HTTP_403_FORBIDDEN)
        vendor = request.user.vendor
        categories = Category.objects.filter(is_active=True, vendor=vendor)
        data = [{"id": c.id, "name": c.name, "is_default": c.is_default} for c in categories]
        return Response(data)
    elif request.method == "POST": 
        if not hasattr(request.user, 'vendor'):
            return Response({"error": "Only vendors can access this endpoint"}, status=status.HTTP_403_FORBIDDEN)
        vendor = request.user.vendor
        name = request.data.get('name')
        description = request.data.get('description')
        
        if not name or not description:
            return Response({'error': 'Name and Description is required'}, status=400)
        
        # FIXED: Basic duplicate prevention per vendor
        if Category.objects.filter(vendor=vendor, name=name).exists():
            return Response({'error': 'Category with this name already exists'}, status=status.HTTP_400_BAD_REQUEST)

        category = Category.objects.create(
            name=name,
            vendor=vendor,
            description=description,
            is_default=False
        )
        return Response({'id': category.id, 'name': category.name,'description':category.description})

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_category(request, pk):
    try:
        if not hasattr(request.user, 'vendor'):
            return Response({'error': 'Only vendors can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
        category = Category.objects.get(pk=pk, vendor=request.user.vendor)
        category.name = request.data.get('name', category.name)
        category.save()
        return Response({'id': category.id, 'name': category.name})
    except Category.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_category(request, pk):
    try:
        if not hasattr(request.user, 'vendor'):
            return Response({'error': 'Only vendors can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
        category = Category.objects.get(pk=pk, vendor=request.user.vendor)
        if category.is_default:
            return Response({'error': 'Cannot delete default category'}, status=status.HTTP_400_BAD_REQUEST)
        category.delete()
        return Response({'detail': 'Product deleted successfully'},status=status.HTTP_200_OK)
    except Category.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    
    
    

    