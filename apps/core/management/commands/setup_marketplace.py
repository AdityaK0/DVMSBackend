from django.core.management.base import BaseCommand
from apps.subscriptions.models import SubscriptionPlan
from django.db import transaction

class Command(BaseCommand):
    help = "Setup marketplace system defaults (subscription plans, etc.)"

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Running marketplace setup script...")

        try:
            with transaction.atomic():
                self.create_subscription_plans()
                # add more setup methods here later

            self.stdout.write(self.style.SUCCESS("✅ Marketplace setup complete!"))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Setup failed: {str(e)}"))
            raise

    def create_subscription_plans(self):
        plans = [
            {
                "name": "Free Plan",
                "plan_type": "free",
                "description": "Free tier with limited features",
                "price": 21,
                "duration_days": 30,
                "sync_limit": 5,
            },
            {
                "name": "Basic Plan",
                "plan_type": "basic",
                "description": "For small vendors",
                "price": 299,
                "duration_days": 30,
                "sync_limit": 50,
            },
            {
                "name": "Premium Plan",
                "plan_type": "premium",
                "description": "For growing businesses",
                "price": 799,
                "duration_days": 30,
                "sync_limit": 200,
            },
            {
                "name": "Enterprise Plan",
                "plan_type": "enterprise",
                "description": "For large scale vendors",
                "price": 1999,
                "duration_days": 30,
                "sync_limit": 1000,
            },
        ]

        for data in plans:
            plan, created = SubscriptionPlan.objects.update_or_create(
                name=data["name"],
                defaults=data
            )

            if created:
                self.stdout.write(f"✅ Created plan: {plan.name} (ID: {plan.id})")
            else:
                self.stdout.write(f"🔄 Updated plan: {plan.name} (ID: {plan.id})")
