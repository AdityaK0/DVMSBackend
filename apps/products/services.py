# will do some product cache or something here may be


from django.db.models import Q,Prefetch
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from apps.products.models import Product,Category
from apps.products.serializers import ProductListSerializer
from apps.dashboard.service import get_product_stats_cached
from django.shortcuts import get_object_or_404
from apps.portfolio.models import Portfolio
from django.http import Http404
from .exceptions import ProductValidationError
from .serializers import ProductSerializer,ProductUpdateSerializer
from django.db import transaction
from apps.core.cache_decorators import redis_cached
from apps.core.events import ProductCreated, ProductUpdated, ProductDeleted



class ProductService:

    @staticmethod
    def get_product(pk,*,context=None):
        """
        Returns a Product object or raises DoesNotExist.
        Business logic stays here; HTTP logic stays in the view.
        """
        print("Really Not hitting the DB :) ::::: ")
        product =  (
            Product.objects
            .select_related("vendor", "category")
            .get(pk=pk, is_active=True, is_archived=False)
        )
        return ProductSerializer(product, context=context).data
    
    
    
    @staticmethod
    def create_product(data, vendor, *, context=None):
        
        category_id = data.get("category")

        if not category_id:
            raise ProductValidationError({"category": "This field is required."})
        
        try:
            category = Category.objects.get(id=category_id, is_active=True)
        except Category.DoesNotExist:
            raise  ProductValidationError({"category": "Invalid category selected."})
        
        
        
        image_urls = data.get("image_urls")
        if image_urls is None:
            raise ProductValidationError({"image_urls": "Image URLs are required."})

        serializer = ProductSerializer(data=data, context=context)
        if serializer.is_valid():
            with transaction.atomic():
                image_urls = data.get('image_urls') or data.getlist('image_urls[]') or []
                sizes = data.get('sizes') or data.getlist('sizes[]') or []
                

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
                
            # Serialize for event payload
            product_data = ProductSerializer(product, context=context).data
            
            
            return product
            
    @staticmethod
    def update_product(pk, data, user, *, context=None):
        
        # 1. Ownership validation
        try:
            product = Product.objects.get(pk=pk, vendor__user=user)
        except Product.DoesNotExist:
            raise ProductValidationError({"detail": "Product not found"})


        # Update normal fields (no image updates here)
        serializer = ProductUpdateSerializer(
            product,
            data=data,
            partial=True,
            context=context
        )
        serializer.is_valid(raise_exception=True)
        
        
        updated_product = serializer.save()

        # -----------------------
        # IMAGE HANDLING
        # -----------------------
        
        existing = updated_product.image_urls or []
        
        # Safely get lists even if sent as single values
        images_to_delete = data.get("images_to_delete", [])
        if isinstance(images_to_delete, str):
            images_to_delete = [images_to_delete]
            
        new_urls = data.get("image_urls", [])
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
        serialized = ProductSerializer(updated_product, context=context).data
        
        # Publish event with standardized payload
        
        return serialized
    
    
    @staticmethod
    def delete_product(pk, data, user, *, context=None):
        
        try:
           product = Product.objects.get(pk=pk, vendor__user=user)
        except Product.DoesNotExist:
            raise ProductValidationError({"detail": "Product not found or you don't have permission"})
        
        vendor_id = product.vendor_id
        product_id = product.id
        
        # Soft delete
        product.is_archived = True
        product.save(update_fields=["is_archived"])
        
        # Publish event after transaction commits
        transaction.on_commit(lambda: ProductDeleted({
            "id": product_id,
            "action": "deleted",
            "data": None,  # No data needed for deleted products
            "metadata": {
                "vendor_id": vendor_id,
            }
        }).publish(bg=True))
        
        return True

def get_vendor_products_combined(
    vendor,
    request=None,
    page=1,
    page_size=10,
    query="",
    include_private=False,
):
    """
    Unified service for fetching vendor products.
    - Supports normal listing and search in one function.
    """
    
    queryset = (
        Product.objects.filter(
            vendor=vendor,
            is_archived=False
        )
        .select_related("vendor", "category")
        .order_by("-created_at")
    )

    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(sku__icontains=query)
        )

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    serializer = ProductListSerializer(
        page_obj.object_list,
        many=True,
        context={"request": request} if request else {},
    )

    product_stats = get_product_stats_cached(vendor)
    paginator_count = product_stats.get("total_active_products", paginator.count)

    return {
        "results": serializer.data,
        "count": paginator_count,
        "total_pages": paginator.num_pages,
        "current_page": int(page),
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
    }





def get_filtered_products(vendor, params, request=None):
    """
    Fetch filtered products for a vendor with pagination and optional filters.
    Reusable across multiple views.
    """
    products = Product.objects.filter(vendor=vendor, is_archived=False)

    # Extract filters
    is_active = params.get("is_active")
    category = params.get("category")
    min_price = params.get("min_price")
    max_price = params.get("max_price")

    # Apply filters
    if is_active is not None:
        products = products.filter(is_active=is_active.lower() == "true")

    if category:
        products = products.filter(category__iexact=category)

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

    # Pagination
    page = params.get("page", 1)
    page_size = params.get("page_size", 10)
    paginator = Paginator(products, page_size)
    page_obj = paginator.get_page(page)

    # Serialize
    serializer = ProductListSerializer(
        page_obj.object_list,
        many=True,
        context={'request': request}
    )

    return {
        "results": serializer.data,
        "count": paginator.count,
        "total_pages": paginator.num_pages,
        "current_page": int(page_obj.number),
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
    }

def get_product_details(vendor, id):
    """
    Safely fetch a single product for a given vendor.
    Returns serialized data or a proper error response.
    """
    try:
        # Fetch the product or raise 404
        product = get_object_or_404(Product, id=id, vendor=vendor, is_active=True)

        # Serialize
        serializer = ProductListSerializer(product, many=False)
        return serializer.data

    except Http404:
        raise 
    except Exception as e:
        raise Exception(f"Error fetching product details: {e}")
        

from django.core.cache import cache


def sync_featured_product(product):
    """
    Sync Product.is_featured with Portfolio.featured_products M2M.
    """

    vendor = product.vendor
    try:
        portfolio = vendor.portfolio
    except Portfolio.DoesNotExist:
        return  
    if product.is_featured:
        portfolio.featured_products.add(product)
        cache.delete(f"portfolio:{vendor.id}")
    else:
        portfolio.featured_products.remove(product)
        cache.delete(f"portfolio:{vendor.id}")



