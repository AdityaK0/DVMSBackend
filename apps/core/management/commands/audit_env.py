from django.conf import settings
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Audit production readiness"

    def handle(self, *args, **options):
        warnings = []

        if settings.DEBUG:
            warnings.append("DEBUG is True")
        if "localhost" in settings.ALLOWED_HOSTS or len(settings.ALLOWED_HOSTS) < 1:
            warnings.append("ALLOWED_HOSTS not properly set")
        if not hasattr(settings, "RAZORPAY_KEY_SECRET"):
            warnings.append("Missing Razorpay configuration")
        if not settings.SECRET_KEY or "django-insecure" in settings.SECRET_KEY:
            warnings.append("Insecure SECRET_KEY")
        if not hasattr(settings, "CORS_ALLOWED_ORIGINS"):
            warnings.append("CORS_ALLOWED_ORIGINS not configured")
        if not hasattr(settings, "CSRF_TRUSTED_ORIGINS"):
            warnings.append("CSRF_TRUSTED_ORIGINS not set")

        if warnings:
            for w in warnings:
                self.stdout.write(self.style.WARNING(f"⚠️ {w}"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ Environment looks production-safe!"))
