

import boto3
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
import uuid

@api_view(['POST'])
def get_presigned_url(request):
    file_name = request.data.get("file_name")
    file_type = request.data.get("file_type")
    # folder = request.data.get("folder", "products")
    folder = request.data.get("folder", "products").strip("/")


    if not file_name or not file_type:
        return Response({"error": "file_name and file_type required"}, status=400)

    s3 = boto3.client(
        "s3",
        # aws_access_key_id=settings.AWS_ACCESS_KEY_ID, let boto3 pick from env/role if on prod the ec2 instance will handle else on local will go with .env file 
        # aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

    # Generate unique filename
    key = f"{folder}/{uuid.uuid4()}-{file_name}"
    
    
    
    presigned_url = s3.generate_presigned_url(
    ClientMethod="put_object",
    Params={
        "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
        "Key": key,
        # "ContentType": file_type,
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
