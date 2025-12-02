# from celery import shared_task
# from apps.core.models import BackgroundTask
# from .telegram_services import TelegramServices


# @shared_task(bind=True)
# def process_telegram_celery(self, task_id, data):
#     task = BackgroundTask.objects.get(id=task_id)

#     try:
#         task.status = BackgroundTask.Status.IN_PROGRESS
#         task.save()

#         TelegramServices.process_telegram_update(data)

#         task.status = BackgroundTask.Status.COMPLETED
#         task.save()

#     except Exception as e:
#         task.status = BackgroundTask.Status.FAILED
#         task.error_message = str(e)
#         task.save()
#         raise e
