from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import Product, Category
from .serializers import ProductSerializer
from apps.subscriptions.permissions import IsSubscribedOrReadOnly
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import Product, Category
from .serializers import ProductSerializer
from .serializers import ProductUpdateSerializer
from .services import *
from .exceptions import ProductValidationError


import logging
logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_detail(request, pk):

    try:
        product = ProductService.get_product(pk,context={"request":request})
    except Product.DoesNotExist:
        return Response({"detail": "Product not found"}, status=404)
    
    if isinstance(product, dict):
        return Response(product)
    
    serializer = ProductSerializer(product, context={"request": request})
    return Response(serializer.data)






# @api_view(['POST'])
# @permission_classes([IsAuthenticated, IsSubscribedOrReadOnly])
# def create_product(request):
#     """Create a new product (text data only)."""
#     if not hasattr(request.user, 'vendor'):
#         return Response(
#             {"error": "Only vendors can create products"},
#             status=status.HTTP_403_FORBIDDEN
#         )

#     vendor = request.user.vendor
#     data = request.data
#     category_id = data.get('category')
#     if not category_id:
#         return Response({"category": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

#     try:
#         category = Category.objects.get(id=category_id, is_active=True)
#     except Category.DoesNotExist:
#         return Response({"category": "Invalid category selected."}, status=status.HTTP_400_BAD_REQUEST)

#     serializer = ProductSerializer(data=data, context={'request': request})
#     if serializer.is_valid():
#         with transaction.atomic():
#             image_urls = data.get('image_urls') or data.getlist('image_urls[]') or []
#             sizes = data.get('sizes') or data.getlist('sizes[]') or []
            

#             # Normalize the data to a clean list
#             if isinstance(image_urls, str):
#                 import json
#                 try:
#                     image_urls = json.loads(image_urls)
#                 except Exception:
#                     image_urls = [image_urls]
#             elif not isinstance(image_urls, (list, tuple)):
#                 image_urls = [image_urls]

#             product = serializer.save(
#                 vendor=vendor,
#                 category=category,
#                 image_urls=image_urls,
#                 primary_image=image_urls[0] if image_urls else None,
#                 sizes=sizes
#             )

#         response_serializer = ProductSerializer(product, context={'request': request})
#         return Response(response_serializer.data, status=status.HTTP_201_CREATED)

#     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(['POST'])
@permission_classes([IsAuthenticated, IsSubscribedOrReadOnly])
def create_product(request):
    """Create a new product (text data only)."""
    if not hasattr(request.user, 'vendor'):
        return Response(
            {"error": "Only vendors can create products"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        product = ProductService.create_product(
            data = request.data,
            vendor = request.user.vendor,
            context= {'request': request},
        ) 
    except ProductValidationError as e:
        raise Response(e.errors,status=status.HTTP_400_BAD_REQUEST)
    
    
    serializer = ProductSerializer(product, context={'request': request})
    return Response(serializer.data,status=status.HTTP_201_CREATED)
               
            




# @api_view(['PUT', 'PATCH'])
# @permission_classes([IsAuthenticated])
# def update_product(request, pk):
#     """Update product; image updates handled manually."""
    
#     try:
#         product = Product.objects.get(pk=pk, vendor__user=request.user)
#     except Product.DoesNotExist:
#         return Response({"detail": "Product not found"}, status=404)

#     # Update normal fields (no image updates here)
#     serializer = ProductUpdateSerializer(
#         product,
#         data=request.data,
#         partial=True
#     )
#     serializer.is_valid(raise_exception=True)
#     updated_product = serializer.save()

#     # -----------------------
#     # IMAGE HANDLING
#     # -----------------------
    
#     existing = updated_product.image_urls or []
    
#     # Safely get lists even if sent as single values
#     images_to_delete = request.data.get("images_to_delete", [])
#     if isinstance(images_to_delete, str):
#         images_to_delete = [images_to_delete]
        
#     new_urls = request.data.get("image_urls", [])
#     if isinstance(new_urls, str):
#         new_urls = [new_urls]

#     # Use sets for O(1) lookups and deduplication
#     delete_set = set(images_to_delete)
#     existing_set = set(existing)
    
#     # Remove deleted images
#     final_urls = [url for url in existing if url not in delete_set]

#     # Add new S3 URLs (avoid duplicates)
#     current_final_set = set(final_urls)
#     for url in new_urls:
#         if url and url not in current_final_set:
#             final_urls.append(url)
#             current_final_set.add(url)

#     updated_product.image_urls = final_urls
#     updated_product.primary_image = final_urls[0] if final_urls else None
#     updated_product.save()
#     sync_featured_product(updated_product)
#     return Response(ProductUpdateSerializer(updated_product).data)





@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_product(request, pk):
    """Update product; image updates handled manually."""
    
    try:
        product = ProductService.update_product(
            pk,
            request.data,
            request.user,
            context={'request': request}
        )
    except ProductValidationError as e:
        return Response(e.errors,status=status.HTTP_400_BAD_REQUEST)    
    
    if isinstance(product, dict):
        return Response(product)
    
    sync_featured_product(product)
    
    serializer = ProductSerializer(product, context={"request": request})
    return Response(serializer.data)
    


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
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


# @api_view(['DELETE'])
# @permission_classes([IsAuthenticated])
# def delete_product(request, pk):
#     """Soft delete a product"""
    
#     try:
#         product = Product.objects.get(pk=pk, vendor__user=request.user)
#     except Product.DoesNotExist:
#         return Response(
#             {"detail": "Product not found or you don't have permission"}, 
#             status=status.HTTP_404_NOT_FOUND
#         )
    
#     # Soft delete
#     product.is_archived = True
#     product.save(update_fields=["is_archived"])
    
#     return Response(status=status.HTTP_204_NO_CONTENT)



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_product(request, pk):
    """Soft delete a product"""
    try:
        ProductService.delete_product(
            pk,
            request.data,
            request.user,
            context={'request': request}
        )
    except ProductValidationError as e:
        return Response(e.errors,status=status.HTTP_400_BAD_REQUEST)
    
    return Response(status=status.HTTP_204_NO_CONTENT)
   
    



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

    data = get_vendor_products_combined(
        vendor,
        request=None,
        page=page,
        page_size=page_size,
        query=query,
        include_private=False,
    )
        
    return Response(data)


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
    
    
    

    