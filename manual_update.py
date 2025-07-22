#!/usr/bin/env python
"""
Manual employee update script
Run this with: python manage.py shell < manual_update.py
"""

from django.contrib.auth.models import User
from leave.models import EmployeeProfile, LeaveBalance, LeaveType
from decimal import Decimal
from datetime import datetime

print("=== MANUAL EMPLOYEE UPDATE ===")

# Employee data from your CSV
employees_data = [
    {
        'username': 'ivan_wong',
        'email': 'ivan.wong@krystal.technology', 
        'first_name': 'Ivan',
        'last_name': 'Wong',
        'date_joined': '2025-07-20',
        'region': 'HK',
        'is_staff': True,
        'annual_leave': 14,
        'sick_leave': 7
    },
    {
        'username': 'krystal',
        'email': 'ivan.wong@krystal.institute',
        'first_name': 'Ivan', 
        'last_name': 'Wong',
        'date_joined': '2020-01-15',
        'region': 'HK', 
        'is_staff': True,
        'annual_leave': 13.5,
        'sick_leave': 0
    },
    {
        'username': 'tim',
        'email': 'tim.tan@krystal.technology',
        'first_name': 'Tim',
        'last_name': 'Tan', 
        'date_joined': '2025-07-20',
        'region': 'CN',
        'is_staff': True,
        'annual_leave': 14,
        'sick_leave': 7
    },
    {
        'username': 'jeff',
        'email': 'jeff.koo@krystal.technology',
        'first_name': 'Jeff',
        'last_name': 'Koo',
        'date_joined': '2025-07-20', 
        'region': 'HK',
        'is_staff': True,
        'annual_leave': 14,
        'sick_leave': 7
    },
    {
        'username': 'danny',
        'email': 'danny.ng@krystal.technology',
        'first_name': 'Danny',
        'last_name': 'Lee',
        'date_joined': '2025-07-20',
        'region': 'HK', 
        'is_staff': False,
        'annual_leave': 14,
        'sick_leave': 7
    }
]

for emp_data in employees_data:
    print(f"\\nProcessing {emp_data['username']}...")
    
    # Create or update user
    user, created = User.objects.get_or_create(
        username=emp_data['username'],
        defaults={
            'email': emp_data['email'],
            'first_name': emp_data['first_name'], 
            'last_name': emp_data['last_name'],
            'is_staff': emp_data['is_staff']
        }
    )
    
    if not created:
        user.email = emp_data['email']
        user.first_name = emp_data['first_name']
        user.last_name = emp_data['last_name'] 
        user.is_staff = emp_data['is_staff']
        user.save()
        print(f"  ✓ Updated user")
    else:
        print(f"  ✓ Created user")
    
    # Create or update profile
    join_date = datetime.strptime(emp_data['date_joined'], '%Y-%m-%d').date()
    profile, profile_created = EmployeeProfile.objects.get_or_create(
        user=user,
        defaults={
            'date_joined': join_date,
            'region': emp_data['region']
        }
    )
    
    if not profile_created:
        profile.date_joined = join_date
        profile.region = emp_data['region']
        profile.save()
        print(f"  ✓ Updated profile")
    else:
        print(f"  ✓ Created profile")
    
    # Update leave balances for 2025
    current_year = 2025
    
    # Annual Leave
    if emp_data['annual_leave'] > 0:
        try:
            leave_type = LeaveType.objects.get(name='Annual Leave')
            balance, _ = LeaveBalance.objects.get_or_create(
                employee=profile,
                leave_type=leave_type,
                year=current_year
            )
            balance.current_year_entitlement = Decimal(str(emp_data['annual_leave']))
            balance.save()
            print(f"  ✓ Annual Leave: {balance.balance}")
        except LeaveType.DoesNotExist:
            print(f"  ✗ Annual Leave type not found")
    
    # Sick Leave  
    if emp_data['sick_leave'] > 0:
        try:
            leave_type = LeaveType.objects.get(name='Sick Leave')
            balance, _ = LeaveBalance.objects.get_or_create(
                employee=profile,
                leave_type=leave_type,
                year=current_year
            )
            balance.current_year_entitlement = Decimal(str(emp_data['sick_leave']))
            balance.save()
            print(f"  ✓ Sick Leave: {balance.balance}")
        except LeaveType.DoesNotExist:
            print(f"  ✗ Sick Leave type not found")

print("\\n=== UPDATE COMPLETED ===")
print("All employee records have been updated!")
