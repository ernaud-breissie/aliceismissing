#!/usr/bin/env python3
import os
import sys
import django
from django.db import IntegrityError

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aliceismissing.settings')
django.setup()

def create_superuser():
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Check if user already exists
        if User.objects.filter(username='admin').exists():
            user = User.objects.get(username='admin')
            user.set_password('admin')
            user.is_staff = True
            user.is_superuser = True
            user.save()
            print("Updated existing superuser 'admin'")
            return
        
        # Create new superuser
        User.objects.create_superuser(
            username='bussiere',
            email='',
            password='admin'
        )
        print("Created new superuser 'admin'")
        
    except IntegrityError:
        print("Error: Could not create superuser - integrity error")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to create superuser: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    create_superuser()

