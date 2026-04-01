#!/usr/bin/env python
"""
Setup script for OptiCart - Creates initial database and admin user
Run from the OptiCart root directory: python setup.py
"""

import os
import sys
import django
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.management import call_command
from django.contrib.auth.models import User

def setup():
    """Run setup operations"""
    print("=" * 50)
    print("OptiCart Setup Script")
    print("=" * 50)
    print()

    # Run migrations
    print("1. Running database migrations...")
    try:
        call_command('migrate')
        print("   ✓ Migrations completed")
    except Exception as e:
        print(f"   ✗ Migration failed: {e}")
        return False

    print()

    # Create admin user
    print("2. Creating admin user...")
    try:
        call_command('create_admin_user')
        print("   ✓ Admin user created/checked")
    except Exception as e:
        print(f"   ✗ Failed to create admin user: {e}")
        return False

    print()
    print("=" * 50)
    print("Setup Complete!")
    print("=" * 50)
    print()
    print("Default Credentials:")
    print("  Username: admin")
    print("  Email: admin@example.com")
    print("  Password: admin123")
    print()
    print("You can now login at: http://localhost:8000/login/")
    print()
    return True

if __name__ == '__main__':
    success = setup()
    sys.exit(0 if success else 1)
