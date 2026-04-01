from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create a hardcoded admin user for testing'

    def handle(self, *args, **options):
        username = 'admin'
        email = 'admin@example.com'
        password = 'admin123'
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User "{username}" already exists'))
            return
        
        # Create the user
        user = User.objects.create_user(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'User "{username}" created successfully'))
        self.stdout.write(f'  Email: {email}')
        self.stdout.write(f'  Password: {password}')
