#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
sys.path.append('/Users/wongivan/company-leave-system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_system.settings')
django.setup()

from django.contrib.auth.models import User
from leave.models import EmployeeProfile, LeaveBalance, LeaveType
import csv
from decimal import Decimal
from datetime import datetime

print("=== CHECKING CURRENT DATA BEFORE UPDATE ===")

# Check current users
employees = [
    ('ivan_wong', 'ivan.wong@krystal.technology'),
    ('tim', 'tim.tan@krystal.technology'), 
    ('jeff', 'jeff.koo@krystal.technology'),
    ('danny', 'danny.ng@krystal.technology'),
    ('krystal', 'ivan.wong@krystal.institute')
]

for username, email in employees:
    print(f"\n--- {username.upper()} ---")
    try:
        user = User.objects.get(username=username)
        print(f"✓ User exists - ID: {user.id}")
        print(f"  Email: {user.email}")
        print(f"  Name: {user.first_name} {user.last_name}")
        print(f"  Is Staff: {user.is_staff}")
        
        try:
            profile = EmployeeProfile.objects.get(user=user)
            print(f"  Profile: {profile.date_joined}, {profile.region}")
            
            balances = LeaveBalance.objects.filter(employee=profile, year=2025)
            print(f"  Leave Balances:")
            for balance in balances:
                print(f"    {balance.leave_type.name}: {balance.balance}")
        except EmployeeProfile.DoesNotExist:
            print("  ✗ No employee profile found!")
            
    except User.DoesNotExist:
        print(f"✗ User {username} NOT FOUND")

print("\n=== IMPORTING CSV DATA ===")

# Read and process the CSV
csv_file = '/Users/wongivan/company-leave-system/ivan_wong_update.csv'
with open(csv_file, 'r') as file:
    reader = csv.DictReader(file)
    
    for row in reader:
        username = row['username']
        email = row['email']
        first_name = row['first_name']
        last_name = row['last_name']
        date_joined = row['date_joined']
        region = row['region']
        is_staff = row['is_staff'].lower() == 'true'
        annual_leave = float(row['annual_leave_balance'])
        sick_leave = float(row['sick_leave_balance'])
        
        print(f"\nProcessing: {username}")
        
        # Parse date
        join_date = datetime.strptime(date_joined, '%Y-%m-%d').date()
        
        # Create or update user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'is_staff': is_staff
            }
        )
        
        if not created:
            # Update existing user
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.is_staff = is_staff
            user.save()
            print(f"  ✓ Updated user {username}")
        else:
            print(f"  ✓ Created user {username}")
        
        # Create or update profile
        profile, profile_created = EmployeeProfile.objects.get_or_create(
            user=user,
            defaults={
                'date_joined': join_date,
                'region': region
            }
        )
        
        if not profile_created:
            profile.date_joined = join_date
            profile.region = region
            profile.save()
            print(f"  ✓ Updated profile")
        else:
            print(f"  ✓ Created profile")
        
        # Update leave balances
        current_year = 2025
        
        # Annual Leave
        if annual_leave > 0:
            try:
                annual_leave_type = LeaveType.objects.get(name='Annual Leave')
                balance, _ = LeaveBalance.objects.get_or_create(
                    employee=profile,
                    leave_type=annual_leave_type,
                    year=current_year,
                    defaults={
                        'opening_balance': Decimal('0.00'),
                        'carried_forward': Decimal('0.00'),
                        'current_year_entitlement': Decimal(str(annual_leave)),
                        'taken': Decimal('0.00')
                    }
                )
                balance.current_year_entitlement = Decimal(str(annual_leave))
                balance.save()  # This will recalculate the balance
                print(f"  ✓ Set Annual Leave: {balance.balance}")
            except LeaveType.DoesNotExist:
                print("  ✗ Annual Leave type not found")
        
        # Sick Leave
        if sick_leave > 0:
            try:
                sick_leave_type = LeaveType.objects.get(name='Sick Leave')
                balance, _ = LeaveBalance.objects.get_or_create(
                    employee=profile,
                    leave_type=sick_leave_type,
                    year=current_year,
                    defaults={
                        'opening_balance': Decimal('0.00'),
                        'carried_forward': Decimal('0.00'),
                        'current_year_entitlement': Decimal(str(sick_leave)),
                        'taken': Decimal('0.00')
                    }
                )
                balance.current_year_entitlement = Decimal(str(sick_leave))
                balance.save()  # This will recalculate the balance
                print(f"  ✓ Set Sick Leave: {balance.balance}")
            except LeaveType.DoesNotExist:
                print("  ✗ Sick Leave type not found")

print("\n=== FINAL VERIFICATION ===")

for username, email in employees:
    try:
        user = User.objects.get(username=username)
        profile = EmployeeProfile.objects.get(user=user)
        balances = LeaveBalance.objects.filter(employee=profile, year=2025)
        
        print(f"\n{username}: {user.first_name} {user.last_name}")
        print(f"  Staff: {user.is_staff}, Region: {profile.region}")
        for balance in balances:
            if balance.balance > 0:
                print(f"  {balance.leave_type.name}: {balance.balance}")
    except:
        print(f"{username}: Error retrieving data")

print("\n=== IMPORT COMPLETED ===")
