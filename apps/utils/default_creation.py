from apps.products.models import Category

BUSINESS_TYPE_CATEGORIES = {
    'clothing': ["T-Shirts", "Jeans", "Jackets", "Shoes"],
    'electronics': ["Mobile Phones", "Laptops", "Cameras", "Accessories"],
    'furniture': ["Sofas", "Beds", "Tables", "Chairs"],
    'other': []
}
    
    
    
def create_default_categories_for_vendor(vendor):
    default_list = BUSINESS_TYPE_CATEGORIES.get(vendor.business_type, [])
    for cat_name in default_list:
        Category.objects.get_or_create(
            name=cat_name,
            vendor=vendor,
            is_default=True
            # defaults={'is_default': True}
        )
    