from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser with admin role'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)
        parser.add_argument('--email', required=True)
        parser.add_argument('--password', required=True)

    def handle(self, *args, **options):
        User.objects.create_user(
            username=options['username'],
            email=options['email'],
            password=options['password'],
            role='admin',
            is_staff=True,
            is_superuser=True
        )
        self.stdout.write(
            self.style.SUCCESS('Successfully created admin user')
        )
        