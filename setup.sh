#!/bin/bash

# Setup script for OptiCart - Creates initial database and admin user

echo "=========================================="
echo "OptiCart Setup Script"
echo "=========================================="
echo ""

cd "$(dirname "$0")/backend" || exit 1

echo "1. Running database migrations..."
python manage.py migrate

echo ""
echo "2. Creating admin user..."
python manage.py create_admin_user

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Default Credentials:"
echo "  Username: admin"
echo "  Email: admin@example.com"
echo "  Password: admin123"
echo ""
echo "You can now login at: http://localhost:8000/login/"
echo ""
