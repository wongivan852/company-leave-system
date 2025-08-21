#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_system.settings')
django.setup()

from django.contrib.auth.models import User
from leave.models import Employee, LeaveBalance, LeaveType
import csv
from datetime import datetime

def load_staff_data():
    print("=== LOADING STAFF DATA FROM CSV ===")
    
    # Load staff from CSV
    with open('staff_list_fixed.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            username = row['username']
            email = row['email']
            first_name = row['first_name']
            last_name = row['last_name']
            region = row['region']
            annual_leave = float(row['annual_leave_balance'])
            sick_leave = float(row['sick_leave_balance'])
            
            # Create or get user
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_staff': True,
                }
            )
            
            if created:
                user.set_password('password123')  # Default password
                user.save()
                print(f"Created user: {username}")
            else:
                print(f"User already exists: {username}")
            
            # Create or get employee profile
            employee, emp_created = Employee.objects.get_or_create(
                user=user,
                defaults={
                    'employee_id': username.replace('.', '').upper()[:10],
                    'department': 'General',
                    'position': 'Staff',
                    'region': region,
                    'date_joined': datetime.strptime(row['date_joined'], '%Y-%m-%d').date() if row['date_joined'] else None,
                }
            )
            
            if emp_created:
                print(f"Created employee profile for: {username}")

if __name__ == "__main__":
    load_staff_data()
    print("\n=== DATA LOADING COMPLETE ===")
