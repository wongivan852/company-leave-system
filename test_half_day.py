#!/usr/bin/env python
"""
Quick test script to verify half-day leave calculations
"""
import os
import sys
import django

# Add the project root to Python path
sys.path.append('/Users/wongivan/company-leave-system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_system.settings')
django.setup()

from leave.models import LeaveApplication, EmployeeProfile, LeaveType
from datetime import datetime, time, date
from django.contrib.auth.models import User

def test_half_day_calculations():
    print("🧪 Testing Half-Day Leave Calculations")
    print("=" * 50)
    
    try:
        # Get a test employee (assuming we have one)
        employee = EmployeeProfile.objects.first()
        if not employee:
            print("❌ No employee found in database")
            return
        
        # Get a leave type
        leave_type = LeaveType.objects.first()
        if not leave_type:
            print("❌ No leave type found in database")
            return
        
        print(f"👤 Testing with employee: {employee.user.username}")
        print(f"📋 Using leave type: {leave_type.name}")
        print()
        
        # Test cases - Use a Monday (weekday)
        test_date = date(2025, 7, 21)  # Monday, July 21, 2025
        
        test_cases = [
            {
                'name': 'AM Only (Half Day)',
                'start': datetime.combine(test_date, time(9, 0)),
                'end': datetime.combine(test_date, time(13, 0)),
                'expected': 0.5
            },
            {
                'name': 'PM Only (Half Day)', 
                'start': datetime.combine(test_date, time(13, 0)),
                'end': datetime.combine(test_date, time(18, 0)),
                'expected': 0.5
            },
            {
                'name': 'Full Day (AM to PM)',
                'start': datetime.combine(test_date, time(9, 0)),
                'end': datetime.combine(test_date, time(18, 0)),
                'expected': 1.0
            }
        ]
        
        for test_case in test_cases:
            print(f"🔍 {test_case['name']}")
            print(f"   Start: {test_case['start'].strftime('%Y-%m-%d %H:%M')}")
            print(f"   End:   {test_case['end'].strftime('%Y-%m-%d %H:%M')}")
            
            # Create temporary application (don't save to DB)
            temp_app = LeaveApplication(
                employee=employee,
                leave_type=leave_type,
                date_from=test_case['start'],
                date_to=test_case['end']
            )
            
            try:
                calculated_days = temp_app.calculate_leave_days()
                print(f"   📊 Calculated: {calculated_days} days")
                print(f"   ✅ Expected:   {test_case['expected']} days")
                
                if calculated_days == test_case['expected']:
                    print(f"   ✅ PASS")
                else:
                    print(f"   ❌ FAIL - Expected {test_case['expected']}, got {calculated_days}")
                    
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
            
            print()
        
        print("🎯 Test Summary: Half-day calculations should work correctly")
        print("   - AM only (9:00-13:00) = 0.5 days")
        print("   - PM only (13:00-18:00) = 0.5 days") 
        print("   - Full day (9:00-18:00) = 1.0 days")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    test_half_day_calculations()
