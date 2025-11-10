from django.shortcuts import render

# Create your views here.


# marketplace/api/uploads.py
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .services.uploads import UploadService

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_files_view(request):
    """
    POST multipart: files under 'uploaded_files'
    Returns list of uploaded file metadata: [{url, file_name, provider}]
    """
    files = request.FILES.getlist('uploaded_files')
    if not files:
        return Response({'uploaded_files': 'No files provided'}, status=status.HTTP_400_BAD_REQUEST)

    upload_service = get_upload_service()
    results = []
    for f in files:
        # optional: validate file size/type here
        # create a BytesIO/seekable object for services expecting file-like
        try:
            file_obj = f.file if hasattr(f, 'file') else f
            meta = upload_service.upload_file(file_obj, filename=f.name, folder='images')
            results.append(meta)
        except Exception as e:
            return Response({'detail': f'Failed to upload {f.name}: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({'files': results}, status=status.HTTP_201_CREATED)



from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import BackgroundTask

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_task_status(request, task_id):
    try:
        task = BackgroundTask.objects.get(id=task_id)
        return Response({
            "id": task.id,
            "task_type": task.task_type,    
            "status": task.status,
            "result_url": task.result_url,
            "error_message": task.error_message,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        })
    except BackgroundTask.DoesNotExist:
        return Response({"detail": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
