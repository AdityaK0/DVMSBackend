from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Product, Category, ProductImage
from .serializers import ProductSerializer, ProductListSerializer, CategorySerializer
import django_filters


# Product List with filters (Public)
@api_view(['GET'])
@permission_classes([AllowAny])
def product_list(request):
    """List all active products with filtering, search, and pagination"""
    
    products = Product.objects.filter(is_active=True)
    
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
        product = Product.objects.get(pk=pk, is_active=True)
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
    
    print("Create Product Data:", data)
    print("Files:", request.FILES)
    
    # Create product
    serializer = ProductSerializer(data=data, context={'request': request})
    
    if serializer.is_valid():
        product = serializer.save(vendor=vendor)
        
        # Handle multiple images
        uploaded_images = request.FILES.getlist('uploaded_images')
        for i, image_file in enumerate(uploaded_images):
            ProductImage.objects.create(
                product=product,
                image=image_file,
                is_primary=(i == 0),  # First image is primary
                alt_text=f"{product.name} image {i+1}"
            )
        
        # Return created product
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
    product.is_active = False
    product.save()
    
    return Response(status=status.HTTP_204_NO_CONTENT)


# Vendor's Products (Dashboard)
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
    products = Product.objects.filter(vendor=vendor).order_by('-created_at')
    
    # Optional filtering for vendor dashboard
    is_active = request.GET.get('is_active')
    if is_active is not None:
        products = products.filter(is_active=is_active.lower() == 'true')
    
    search = request.GET.get('search')
    if search:
        products = products.filter(
            Q(name__icontains=search) | 
            Q(sku__icontains=search)
        )
    
    # Pagination
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 10)
    
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

# from rest_framework import generics, permissions, status
# from rest_framework.response import Response
# from django_filters.rest_framework import DjangoFilterBackend
# from rest_framework.filters import SearchFilter, OrderingFilter
# from .models import Product, Category
# from .serializers import ProductSerializer, ProductListSerializer, CategorySerializer
# from shared.permissions import IsVendorOwnerOrReadOnly
# import django_filters

# class ProductFilter(django_filters.FilterSet):
#     min_price = django_filters.NumberFilter(field_name="price", lookup_expr='gte')
#     max_price = django_filters.NumberFilter(field_name="price", lookup_expr='lte')
#     in_stock = django_filters.BooleanFilter(method='filter_in_stock')

#     class Meta:
#         model = Product
#         fields = ['category', 'vendor', 'is_featured', 'is_active']

#     def filter_in_stock(self, queryset, name, value):
#         if value:
#             return queryset.filter(stock_quantity__gt=0)
#         return queryset

# class ProductListView(generics.ListAPIView):
#     queryset = Product.objects.filter(is_active=True)
#     serializer_class = ProductListSerializer
#     permission_classes = [permissions.AllowAny]
#     filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
#     filterset_class = ProductFilter
#     search_fields = ['name', 'description', 'sku']
#     ordering_fields = ['name', 'price', 'created_at']
#     ordering = ['-created_at']

# class ProductDetailView(generics.RetrieveAPIView):
#     queryset = Product.objects.filter(is_active=True)
#     serializer_class = ProductSerializer
#     permission_classes = [permissions.AllowAny]

# class ProductCreateView(generics.CreateAPIView):
#     serializer_class = ProductSerializer
#     permission_classes = [permissions.IsAuthenticated]

#     def perform_create(self, serializer):
#         vendor = self.request.user.vendor
#         serializer.save(vendor=vendor)

# class ProductUpdateView(generics.UpdateAPIView):
#     serializer_class = ProductSerializer
#     permission_classes = [IsVendorOwnerOrReadOnly]

#     def get_queryset(self):
#         return Product.objects.filter(vendor__user=self.request.user)

# class ProductDeleteView(generics.DestroyAPIView):
#     permission_classes = [IsVendorOwnerOrReadOnly]

#     def get_queryset(self):
#         return Product.objects.filter(vendor__user=self.request.user)

#     def destroy(self, request, *args, **kwargs):
#         instance = self.get_object()
#         instance.is_active = False  # Soft delete
#         instance.save()
#         return Response(status=status.HTTP_204_NO_CONTENT)

# class CategoryListView(generics.ListAPIView):
#     queryset = Category.objects.filter(is_active=True)
#     serializer_class = CategorySerializer
#     permission_classes = [permissions.AllowAny]

# class VendorCatalogView(generics.ListAPIView):
#     serializer_class = ProductListSerializer
#     permission_classes = [permissions.AllowAny]

#     def get_queryset(self):
#         vendor_id = self.kwargs['vendor_id']
#         return Product.objects.filter(
#             vendor_id=vendor_id, 
#             is_active=True,
#             stock_quantity__gt=0
#         )