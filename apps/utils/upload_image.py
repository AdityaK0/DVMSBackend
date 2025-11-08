# apps/products/utils.py

from apps.products.models import ProductImage
from apps.vendors.models import Vendor
from apps.portfolio.models import PortfolioCollection  # adjust import if needed
import logging
logger = logging.getLogger(__name__)
import cloudinary.uploader


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


#   -- ADDING SECURE = TRUE CAN UPLOAD IN HTTPS  image=result["secure_url"],

from cloudinary.uploader import upload,destroy
from apps.products.models import ProductImage

def upload_product_images(product, files):
    images = []
    for i, file in enumerate(files):
        result = upload(
            file,
            folder=f"products/{product.id}/",  # dynamic folder
            overwrite=True,
            resource_type="image",
            secure=True
        )
        img = ProductImage.objects.create(
            product=product,
            # image=result['public_id'],  # store public_id in CloudinaryField
            image=result['secure_url'],  # store secure_url in CloudinaryField
            is_primary=(i == 0),
            alt_text=f"{product.name} image {i+1}"
        )
        images.append(img)
    return images



def delete_product_images(product_image):
    result = None
    try:
        public_id = str(product_image.image)
        result = cloudinary.uploader.destroy(public_id, resource_type="image")
    except Exception as e:
        logger.error("Failed to delete image: %s", e)
    
    product_image.delete()    
    return result

def upload_collection_image(collection, file):
    """
    Upload a single collection image to Cloudinary and update the model.
    """
    if not file:
        return None
    
    # Upload image to Cloudinary
    result = upload(
        file,
        folder=f"collections/{collection.id}/",
        overwrite=True,
        resource_type="image",
        secure=True
        
    )
    print("*"*100 , result)
    logger.info("UPLOAD RESULT: %s", result) 
    # Assuming PortfolioCollection has a field like `image` (CloudinaryField or CharField for public_id)
    # collection.cover_image = result["public_id"]
    collection.cover_image = result["secure_url"]
    
    collection.save(update_fields=["cover_image"])
    
    return result



from cloudinary.uploader import upload, destroy

def upload_portfolio_banner(file, portfolio):
    """Upload banner image (single file)"""
    result = upload(
        file,
        folder=f"portfolio/{portfolio.id}/banner/",
        overwrite=True,
        resource_type="image",
        secure=True
    )

    # return Cloudinary URL / public ID
    return result["secure_url"]


def upload_portfolio_carousel(files, portfolio):
    """Upload multiple carousel images"""
    uploaded_images = []

    for file in files:
        result = upload(
            file,
            folder=f"portfolio/{portfolio.id}/carousel/",
            overwrite=True,
            resource_type="image",
            secure=True
        )
        uploaded_images.append(result["secure_url"])  # store only URL

    return uploaded_images


# def upload_collection_image(collection, file):
#     """
#     Upload or replace the collection cover image in Cloudinary.
#     Ensures proper folder structure and file naming.
#     """
#     if not file:
#         return None

#     # Ensure collection has an ID (important for folder path)
#     if not collection.id:
#         collection.save()

#     result = upload(
#         file,
#         folder=f"collections/{collection.id}",
#         use_filename=True,
#         unique_filename=False,
#         overwrite=True,
#         resource_type="image"
#     )

#     print("Uploaded file to folder:", result.get("public_id"))
#     print("Full URL:", result.get("secure_url"))

#     collection.cover_image = result["public_id"]
#     collection.save(update_fields=["cover_image"])

#     return result




def upload_vendor_logo(vendor, file):
    """
    Uploads vendor logo to Cloudinary and updates the vendor instance.
    """
    if file:
        vendor.logo = file  # CloudinaryField will handle the upload
        vendor.save()
        return vendor.logo
    return None
