# apps/products/utils.py

from apps.products.models import ProductImage
from apps.vendors.models import Vendor

# def upload_product_images(product, files):
#     """
#     Handle bulk upload of product images.
#     - Assigns first image as primary.
#     - Auto-attaches alt text.
#     - Returns list of created ProductImage instances.
#     """
#     images = []
#     for i, file in enumerate(files):
#         img = ProductImage.objects.create(
#             product=product,
#             image=file,  # Cloudinary handles upload
#             folder=f"products/{product.id}/",
#             is_primary=(i == 0),
#             alt_text=f"{product.name} image {i+1}"
#         )
#         images.append(img)
#     return images



from cloudinary.uploader import upload
from apps.products.models import ProductImage

def upload_product_images(product, files):
    images = []
    for i, file in enumerate(files):
        result = upload(
            file,
            folder=f"products/{product.id}/",  # dynamic folder
            overwrite=True,
            resource_type="image"
        )
        img = ProductImage.objects.create(
            product=product,
            image=result['public_id'],  # store public_id in CloudinaryField
            is_primary=(i == 0),
            alt_text=f"{product.name} image {i+1}"
        )
        images.append(img)
    return images




def upload_vendor_logo(vendor, file):
    """
    Uploads vendor logo to Cloudinary and updates the vendor instance.
    """
    if file:
        vendor.logo = file  # CloudinaryField will handle the upload
        vendor.save()
        return vendor.logo
    return None
