# apps/products/utils.py
from apps.core.services.uploads import UploadService
from apps.products.models import ProductImage



def upload_product_images_async(product, files):
    service = UploadService()
    bg_tasks = []
    for file in files:
        bg = service.upload_async(file, folder=f"products/{product.id}/", link_to=product, task_type="IMAGE_UPLOAD")
        bg_tasks.append(bg)
    return bg_tasks





def upload_product_images(product, files):
    """
    Upload multiple product images via core UploadService.
    The first image is marked as primary.
    """
    service = UploadService()
    images = []

    for i, file in enumerate(files):
        upload_record = service.upload(file, folder=f"products/{product.id}/", link_to=product)

        img = ProductImage.objects.create(
            product=product,
            image=upload_record.url,
            is_primary=(i == 0),
            alt_text=f"{product.name} image {i+1}"
        )
        images.append(img)

    return images


def delete_product_image(product_image):
    """
    Delete product image from cloud and DB.
    """
    service = UploadService()
    public_id = product_image.image  # only if you stored Cloudinary public_id
    service._delete_from_cloudinary(public_id)
    product_image.delete()




