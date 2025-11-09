from rest_framework.views import exception_handler
from django.core.exceptions import RequestDataTooBig
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    if isinstance(exc, RequestDataTooBig):
        return Response(
            {"detail": "Uploaded data too large. Max allowed size is 20MB."},
            status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        )

    return exception_handler(exc, context)
