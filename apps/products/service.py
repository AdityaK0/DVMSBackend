# will do some product cache or something here may be


from django.core.paginator import Paginator
from django.db.models import Prefetch
from apps.products.models import Product, ProductImage
from apps.products.serializers import ProductListSerializer
from apps.dashboard.service import get_product_stats_cached


def get_vendor_products_data(vendor, request=None, page=1, page_size=10, include_private=False):
    """
    Reusable service function to get vendor products with pagination and serialization.
    """

    # Base queryset
    queryset = Product.objects.filter(
        vendor=vendor,
        is_active=True,
        is_archived=False
    ).select_related('vendor', 'category') \
    .prefetch_related(
        Prefetch(
            'images',
            queryset=ProductImage.objects.all(),
            to_attr='images_prefetched'
        )
    ).order_by('-created_at')

    # Pagination
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    # Serialize data
    serializer = ProductListSerializer(
        page_obj.object_list,
        many=True,
        context={'request': request} if request else {}
    )

    # Product statistics (cached)
    product_stats = get_product_stats_cached(vendor)
    paginator_count = product_stats.get("total_active_products", paginator.count)

    # Final response data
    return {
        'results': serializer.data,
        'count': paginator_count,
        'total_pages': paginator.num_pages,
        'current_page': int(page),
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    }



