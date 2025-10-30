from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.core.paginator import Paginator
from django.db.models import Q,Prefetch
from .models import Product, Category, ProductImage
from .serializers import ProductSerializer, ProductListSerializer, CategorySerializer
from ..utils.upload_image import upload_product_images
from django.db import connection
from .service import get_vendor_products_data

# Product List with filters (Public)
@api_view(['GET'])
@permission_classes([AllowAny])
def product_list(request):
    """List all active products with filtering, search, and pagination"""
    
    products = Product.objects.filter(is_active=True,is_archived=False)
    
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
        # product = Product.objects.get(pk=pk, is_active=True)
        product = Product.objects.get(pk=pk)
        
    except Product.DoesNotExist:
        return Response(
            {"detail": "Product not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = ProductSerializer(product, context={'request': request})
    return Response(serializer.data)


# Create Product (Vendor only)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def create_product(request):
    """Create a new product"""
    
    # Check if user is a vendor
    if not hasattr(request.user, 'vendor'):
        return Response(
            {"error": "Only vendors can create products"}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    vendor = request.user.vendor
    
    # Prepare data
    # data = request.data.copy()
    # # OR
    data = request.POST.copy()
    data['vendor'] = vendor.id
    # custom category integration
    
    category_id = data.get('category')
    if not category_id:
        return Response({"category": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        category = Category.objects.get(id=category_id, is_active=True)
    except Category.DoesNotExist:
        return Response({"category": "Invalid category selected."}, status=status.HTTP_400_BAD_REQUEST)
    
    print("Create Product Data:", data)
    print("Files:", request.FILES)
    
    # Create product
    serializer = ProductSerializer(data=data, context={'request': request})
    
    if serializer.is_valid():
        product = serializer.save(vendor=vendor,category=category)
        
        # Handle multiple images
        uploaded_images = request.FILES.getlist('uploaded_images')
        if uploaded_images:
            upload_product_images(product, uploaded_images)

        response_serializer = ProductSerializer(product, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Update Product (Vendor only - their own products)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def update_product(request, pk):
    """Update a product"""
    
    try:
        product = Product.objects.get(pk=pk, vendor__user=request.user)
    except Product.DoesNotExist:
        return Response(
            {"detail": "Product not found or you don't have permission"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Prepare data
    data = request.data.copy()
    partial = request.method == 'PATCH'
    
    print("Update Product Data:", data)
    print("Files:", request.FILES)
    
    serializer = ProductSerializer(
        product, 
        data=data, 
        partial=partial, 
        context={'request': request}
    )
    
    if serializer.is_valid():
        updated_product = serializer.save()
        
        # Handle new images if provided
        uploaded_images = request.FILES.getlist('uploaded_images')
        if uploaded_images:
            # Optional: Remove old images if you want to replace all
            # product.images.all().delete()
            
            for i, image_file in enumerate(uploaded_images):
                ProductImage.objects.create(
                    product=updated_product,
                    image=image_file,
                    is_primary=(i == 0 and not product.images.filter(is_primary=True).exists()),
                    alt_text=f"{updated_product.name} image {i+1}"
                )
        
        response_serializer = ProductSerializer(updated_product, context={'request': request})
        return Response(response_serializer.data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    product.save()
    
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
    product.save()
    
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

    data = get_vendor_products_data(vendor, request=request, page=page, page_size=page_size)
    return Response(data)


# Vendor's Products (Dashboard)
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def vendor_products(request):
#     """Get all products for the current vendor"""
    
#     if not hasattr(request.user, 'vendor'):
#         return Response(
#             {"error": "Only vendors can access this endpoint"}, 
#             status=status.HTTP_403_FORBIDDEN
#         )
    
#     vendor = request.user.vendor
#     if not vendor:
#         vendor = request.user
#     # products = Product.objects.filter(vendor=vendor,is_active=True,is_archived=False).order_by('-created_at')
#     # print(connection.queries , "ALL PRODUCT QUERRY >>>>>> ")
#     # products = Product.objects.filter(
#     #     vendor=vendor,
#     #     is_active=True,
#     #     is_archived=False
#     # ).select_related('vendor', 'category') \
#     #  .prefetch_related('images') \
#     #  .order_by('-created_at')
     
     
#     products = Product.objects.filter(
#         vendor=vendor,
#         is_active=True,
#         is_archived=False
#     ).select_related('vendor', 'category') \
#     .prefetch_related(
#         Prefetch(
#             'images',
#             queryset=ProductImage.objects.all(),
#             to_attr='images_prefetched'  # store in a custom attribute
#         )
#     ) \
#     .order_by('-created_at')
    
    
    
#     try:
#         page = int(request.GET.get('page', 1))
#     except (TypeError, ValueError):
#         page = 1
        
#     try:
#         page_size = int(request.GET.get('page_size', 10))
#     except (TypeError, ValueError):
#         page_size = 10
    
#     paginator = Paginator(products, page_size)
#     page_obj = paginator.get_page(page)
    
#     serializer = ProductListSerializer(
#         page_obj.object_list, 
#         many=True, 
#         context={'request': request}
#     )
#     # paginator_count  = paginator.count
#     product_stats = get_product_stats_cached(vendor)
#     paginator_count = product_stats.get("total_active_products")
    
#     return Response({
#         'results': serializer.data,
#         'count': paginator_count,
#         'total_pages': paginator.num_pages,
#         'current_page': int(page),
#         'has_next': page_obj.has_next(),
#         'has_previous': page_obj.has_previous(),
#     })


# Vendor Catalog (Public - specific vendor's products)
@api_view(['GET'])
@permission_classes([AllowAny])
def vendor_catalog(request, vendor_id):
    """Get all active products for a specific vendor"""
    
    products = Product.objects.filter(
        vendor_id=vendor_id,
        is_active=True,
        stock_quantity__gt=0
    ).order_by('-created_at')
    
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
    categories = Category.objects.filter(is_active=True)
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_products(request):
    """Optimized: Search products for the current vendor"""
    
    user = request.user
    vendor = getattr(user, "vendor", None)
    if not vendor:
        return Response(
            {"error": "Only vendors can access this endpoint"},
            status=status.HTTP_403_FORBIDDEN
        )

    query = request.GET.get("q", "").strip()
    
    products_qs = (
        Product.objects.filter(vendor=vendor, is_active=True, is_archived=False)
        .select_related("vendor", "category")
        .prefetch_related(
            Prefetch(
                "images",
                queryset=ProductImage.objects.all(),
                to_attr="images_prefetched"
            )
        )
    )

    if query:
        products_qs = products_qs.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(sku__icontains=query)
        )

    # Pagination handling (safe + integer conversion)
    try:
        page = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        page = 1

    try:
        page_size = int(request.GET.get("page_size", 10))
    except (TypeError, ValueError):
        page_size = 10

    paginator = Paginator(products_qs.order_by("-created_at"), page_size)
    page_obj = paginator.get_page(page)

    serializer = ProductListSerializer(
        page_obj.object_list,
        many=True,
        context={"request": request}
    )

    return Response({
        "results": serializer.data,
        "count": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": page,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
    })


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
    products = Product.objects.filter(vendor=vendor,is_archived=False)

    # Get filters
    is_active = request.GET.get("is_active")
    category = request.GET.get("category") or None
    min_price = request.GET.get("min_price") or None
    max_price = request.GET.get("max_price") or None
    # breakpoint()
    # Apply filters
    if is_active is not None:
        products = products.filter(is_active=is_active.lower() == "true")

    if category:
        products = products.filter(category__iexact=category)

    if min_price:
        try:
            min_price = float(min_price)
            products = products.filter(price__gte=min_price)
        except ValueError:
            pass  # ignore invalid numbers

    if max_price:
        try:
            max_price = float(max_price)
            products = products.filter(price__lte=max_price)
        except ValueError:
            pass

    # Pagination
    page = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 10)
    paginator = Paginator(products, page_size)
    page_obj = paginator.get_page(page)

    serializer = ProductListSerializer(
        page_obj.object_list,
        many=True,
        context={'request': request}
    )

    return Response({
        "results": serializer.data,
        "count": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": int(page),
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
    })




@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def vendor_categories(request):
    if request.method == "GET":
        vendor = request.user.vendor
        categories = Category.objects.filter(is_active=True, vendor=vendor)
        data = [{"id": c.id, "name": c.name, "is_default": c.is_default} for c in categories]
        return Response(data)
    elif request.method == "POST": 
        vendor = request.user.vendor
        name = request.data.get('name')
        description = request.data.get('description')
        
        if not name or not description:
            return Response({'error': 'Name and Description is required'}, status=400)
        
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
        category = Category.objects.get(pk=pk, vendor=request.user.vendor)
        if category.is_default:
            return Response({'error': 'Cannot delete default category'}, status=status.HTTP_400_BAD_REQUEST)
        category.delete()
        return Response({'detail': 'Product deleted successfully'},status=status.HTTP_200_OK)
    except Category.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)