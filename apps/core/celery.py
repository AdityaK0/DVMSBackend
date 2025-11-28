import os
from celery import Celery
from celery.signals import worker_ready

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marketplace.settings")

celery_app = Celery("marketplace")   # ✔ MUST be named celery_app
celery_app.config_from_object("django.conf:settings", namespace="CELERY")
celery_app.autodiscover_tasks()


@worker_ready.connect
def warmup_on_worker_start(sender, **kwargs):
    from apps.core.tasks import celery_warmup
    print("🚀 Celery worker ready - running warmup task...")
    celery_warmup.delay()