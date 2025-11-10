# # views.py
# import time
# import cloudinary
# import cloudinary.uploader
# import cloudinary.utils
# from rest_framework.decorators import api_view
# from rest_framework.response import Response
# from django.conf import settings
# @api_view(['POST'])
# def get_presigned_url(request):
#     folder = request.data.get('folder', 'misc')
#     timestamp = int(time.time())
#     params_to_sign = {
#         "timestamp": timestamp,
#         "folder": folder
#     }
#     signature = cloudinary.utils.api_sign_request(params_to_sign, settings.CLOUDINARY_STORAGE['CLOUDINARY_API_SECRET'])

#     return Response({
#         "cloud_name": settings.CLOUDINARY_STORAGE['CLOUDINARY_CLOUD_NAME'],
#         "api_key": settings.CLOUDINARY_STORAGE['CLOUDINARY_API_KEY'],
#         "timestamp": timestamp,
#         "signature": signature
#     })


import boto3
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
import uuid

@api_view(['POST'])
def get_presigned_url(request):
    print("BUCKET NAME == * "*10,settings.AWS_STORAGE_BUCKET_NAME)
    file_name = request.data.get("file_name")
    file_type = request.data.get("file_type")
    folder = request.data.get("folder", "products")

    if not file_name or not file_type:
        return Response({"error": "file_name and file_type required"}, status=400)

    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

    # Generate unique filename
    key = f"{folder}/{uuid.uuid4()}-{file_name}"
    
    
    presigned_url = s3.generate_presigned_url(
    ClientMethod="put_object",
    Params={
        "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
        "Key": key,
        "ContentType": file_type,
    },
    ExpiresIn=120,
    )

    # Final public URL to save in DB
    # final_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{key}"
    final_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{key}"

    
    
    return Response({
        "upload_url": presigned_url,
        "final_url": final_url
    })
