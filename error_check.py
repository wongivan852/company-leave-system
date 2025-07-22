#!/usr/bin/env python
"""
Error monitoring script for the Django leave system
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.append('/Users/wongivan/company-leave-system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_system.settings')
django.setup()

def check_for_errors():
    print("🔍 Django Leave System - Error Check")
    print("=" * 50)
    
    errors_found = []
    
    # Check 1: Database connectivity
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        print("✅ Database connection: OK")
    except Exception as e:
        errors_found.append(f"❌ Database connection: {e}")
    
    # Check 2: Models integrity
    try:
        from leave.models import LeaveApplication, EmployeeProfile, LeaveType
        
        # Check if we have essential data
        employee_count = EmployeeProfile.objects.count()
        leave_type_count = LeaveType.objects.count()
        
        print(f"✅ Models: {employee_count} employees, {leave_type_count} leave types")
        
        if employee_count == 0:
            errors_found.append("⚠️  No employees found in database")
        if leave_type_count == 0:
            errors_found.append("⚠️  No leave types found in database")
            
    except Exception as e:
        errors_found.append(f"❌ Models error: {e}")
    
    # Check 3: Forms validation
    try:
        from leave.forms import LeaveApplicationForm
        from datetime import date, datetime, time
        
        # Test form with valid data
        if EmployeeProfile.objects.exists():
            employee = EmployeeProfile.objects.first()
            
            form_data = {
                'leave_type': LeaveType.objects.first().id if LeaveType.objects.exists() else None,
                'start_date': date(2025, 7, 21),  # Use Monday instead of today (Sunday)
                'start_time': 'AM',
                'end_date': date(2025, 7, 21),    # Use Monday instead of today (Sunday)
                'end_time': 'PM',
                'reason': 'Test reason'
            }
            
            form = LeaveApplicationForm(data=form_data, employee=employee)
            if form.is_valid():
                print("✅ Form validation: OK")
            else:
                errors_found.append(f"❌ Form validation: {form.errors}")
        else:
            errors_found.append("⚠️  Cannot test form - no employees")
            
    except Exception as e:
        errors_found.append(f"❌ Form validation error: {e}")
    
    # Check 4: URL patterns
    try:
        from django.urls import reverse
        urls_to_check = [
            'leave:login',
            'leave:dashboard', 
            'leave:apply_leave',
            'leave:leave_applications'
        ]
        
        for url_name in urls_to_check:
            try:
                reverse(url_name)
            except Exception as e:
                errors_found.append(f"❌ URL '{url_name}': {e}")
        
        print("✅ URL patterns: OK")
        
    except Exception as e:
        errors_found.append(f"❌ URL patterns error: {e}")
    
    # Check 5: Template rendering
    try:
        from django.template.loader import get_template
        templates_to_check = [
            'leave/base.html',
            'leave/login.html',
            'leave/dashboard.html',
            'leave/apply_leave.html'
        ]
        
        for template_name in templates_to_check:
            try:
                get_template(template_name)
            except Exception as e:
                errors_found.append(f"❌ Template '{template_name}': {e}")
        
        print("✅ Templates: OK")
        
    except Exception as e:
        errors_found.append(f"❌ Template system error: {e}")
    
    # Check 6: Dependencies
    try:
        import holidays
        print("✅ Dependencies (holidays): OK")
    except ImportError:
        errors_found.append("❌ Missing dependency: holidays")
    
    # Summary
    print("\n" + "=" * 50)
    if errors_found:
        print(f"❌ {len(errors_found)} error(s) found:")
        for error in errors_found:
            print(f"   {error}")
    else:
        print("✅ No errors detected - system appears healthy!")
        
    return len(errors_found) == 0

if __name__ == "__main__":
    check_for_errors()
