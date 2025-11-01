# will do some product cache or something here may be


from django.db.models import Q,Prefetch
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from apps.products.models import Product, ProductImage
from apps.products.serializers import ProductListSerializer
from apps.dashboard.service import get_product_stats_cached


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

    # ✅ Base queryset
    queryset = (
        Product.objects.filter(
            vendor=vendor,
            is_active=True,
            is_archived=False,
        )
        .select_related("vendor", "category")
        .prefetch_related(
            Prefetch(
                "images",
                queryset=ProductImage.objects.all(),
                to_attr="images_prefetched",
            )
        )
        .order_by("-created_at")
    )

    # ✅ Search support
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(sku__icontains=query)
        )

    # ✅ Pagination
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    # ✅ Serialize
    serializer = ProductListSerializer(
        page_obj.object_list,
        many=True,
        context={"request": request} if request else {},
    )

    # ✅ Optional cached stats (for total count)
    product_stats = get_product_stats_cached(vendor)
    paginator_count = product_stats.get("total_active_products", paginator.count)

    # ✅ Final response
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




# def get_vendor_products_data(vendor, request=None, page=1, page_size=10, include_private=False):
#     """
#     Reusable service function to get vendor products with pagination and serialization.
#     """

#     # Base queryset
#     queryset = Product.objects.filter(
#         vendor=vendor,
#         is_active=True,
#         is_archived=False
#     ).select_related('vendor', 'category') \
#     .prefetch_related(
#         Prefetch(
#             'images',
#             queryset=ProductImage.objects.all(),
#             to_attr='images_prefetched'
#         )
#     ).order_by('-created_at')

#     # Pagination
#     paginator = Paginator(queryset, page_size)
#     page_obj = paginator.get_page(page)

#     # Serialize data
#     serializer = ProductListSerializer(
#         page_obj.object_list,
#         many=True,
#         context={'request': request} if request else {}
#     )

#     # Product statistics (cached)
#     product_stats = get_product_stats_cached(vendor)
#     paginator_count = product_stats.get("total_active_products", paginator.count)

#     # Final response data
#     return {
#         'results': serializer.data,
#         'count': paginator_count,
#         'total_pages': paginator.num_pages,
#         'current_page': int(page),
#         'has_next': page_obj.has_next(),
#         'has_previous': page_obj.has_previous(),
#     }



# def get_search_products(vendor, request=None,query="",page=1, page_size=10):
    
#     """Optimized: Search products for the current vendor"""
    
#     # above_not_needed
    
#     products_qs = (
#         Product.objects.filter(vendor=vendor, is_active=True, is_archived=False)
#         .select_related("vendor", "category")
#         .prefetch_related(
#             Prefetch(
#                 "images",
#                 queryset=ProductImage.objects.all(),
#                 to_attr="images_prefetched"
#             )
#         )
#     )

#     if query:
#         products_qs = products_qs.filter(
#             Q(name__icontains=query)
#             | Q(description__icontains=query)
#             | Q(sku__icontains=query)
#         )

#     # Pagination handling (safe + integer conversion)

#     paginator = Paginator(products_qs.order_by("-created_at"), page_size)
#     page_obj = paginator.get_page(page)

#     serializer = ProductListSerializer(
#         page_obj.object_list,
#         many=True,
#         context={"request": request}
#     )

#     return {
#         "results": serializer.data,
#         "count": paginator.count,
#         "total_pages": paginator.num_pages,
#         "current_page": page,
#         "has_next": page_obj.has_next(),
#         "has_previous": page_obj.has_previous(),
#     }