

# core/models.py
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class UploadFile(models.Model):
    provider = models.CharField(max_length=50, default="cloudinary")  # or s3
    url = models.URLField(max_length=1024)
    public_id = models.CharField(max_length=512, blank=True, null=True)
    folder = models.CharField(max_length=255, blank=True, null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.provider} - {self.url}"



class BackgroundTask(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        IN_PROGRESS = "IN_PROGRESS"
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"

    class TaskType(models.TextChoices):
        IMAGE_UPLOAD = "IMAGE_UPLOAD"
        PRODUCT_CREATION = "PRODUCT_CREATION"
        TELEGRAM_LINK = "TELEGRAM_LINK"  

    task_type = models.CharField(max_length=50, choices=TaskType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    upload_type = models.CharField(max_length=100, blank=True, null=True) 
    result_data = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    # link to any model (product, vendor, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    celery_task_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.task_type} ({self.status})"
