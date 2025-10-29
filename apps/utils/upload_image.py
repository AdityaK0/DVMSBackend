# apps/products/utils.py

from apps.products.models import ProductImage
from apps.vendors.models import Vendor
from apps.portfolio.models import PortfolioCollection  # adjust import if needed


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



from cloudinary.uploader import upload,destroy
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



# def upload_collection_image(collection, file):
#     """
#     Upload a single collection image to Cloudinary and update the model.
#     """
#     if not file:
#         return None
    
#     # Upload image to Cloudinary
#     result = upload(
#         file,
#         folder=f"collections/{collection.id}/",
#         overwrite=True,
#         resource_type="image"
#     )

#     # Assuming PortfolioCollection has a field like `image` (CloudinaryField or CharField for public_id)
#     collection.image = result["public_id"]
#     collection.save(update_fields=["image"])
    
#     return result


def upload_collection_image(collection, file):
    """
    Upload or replace the collection image in Cloudinary.
    """
    if not file:
        return None

    # Delete old image if it exists
    if collection.image:
        try:
            destroy(collection.image)  # delete by public_id
        except Exception as e:
            print("Cloudinary delete error:", e)

    # Upload new image
    result = upload(
        file,
        folder=f"collections/{collection.id}/",
        overwrite=True,
        resource_type="image"
    )

    # Update collection with new public_id
    collection.image = result["public_id"]
    collection.save(update_fields=["image"])

    return result



def upload_vendor_logo(vendor, file):
    """
    Uploads vendor logo to Cloudinary and updates the vendor instance.
    """
    if file:
        vendor.logo = file  # CloudinaryField will handle the upload
        vendor.save()
        return vendor.logo
    return None
