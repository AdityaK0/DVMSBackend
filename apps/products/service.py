# will do some product cache or something here may be


from django.db.models import Q,Prefetch
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from apps.products.models import Product
from apps.products.serializers import ProductListSerializer
from apps.dashboard.service import get_product_stats_cached
from django.shortcuts import get_object_or_404
from apps.portfolio.models import Portfolio
from django.http import Http404



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
    else:
        portfolio.featured_products.remove(product)
