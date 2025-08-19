from django.contrib import admin
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib import messages
from .models import (
    Employee, LeaveType, LeaveApplication, PendingRegistration,
    SpecialWorkClaim, SpecialLeaveApplication, SpecialLeaveBalance,
    EmployeeImport, LeaveBalance
)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['user', 'employee_id', 'department', 'position', 'company', 'region', 'date_joined']
    search_fields = ['user__first_name', 'user__last_name', 'employee_id', 'department', 'user__email']
    list_filter = ['department', 'company', 'region']
    date_hierarchy = 'date_joined'

@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'max_days_per_year', 'requires_approval']
    list_filter = ['requires_approval']

@admin.register(LeaveApplication)
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'date_from', 'date_to', 'days_applied', 'status', 'created_at']
    list_filter = ['status', 'leave_type', 'created_at']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'reason']
    date_hierarchy = 'created_at'
    readonly_fields = ['days_applied', 'created_at', 'updated_at']

@admin.register(SpecialWorkClaim)
class SpecialWorkClaimAdmin(admin.ModelAdmin):
    list_display = ['employee', 'event_name', 'work_date', 'session', 'status', 'credits_earned', 'created_at']
    list_filter = ['status', 'session', 'priority', 'created_at']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'event_name']
    date_hierarchy = 'created_at'
    readonly_fields = ['credits_earned', 'created_at', 'updated_at']

@admin.register(SpecialLeaveApplication)
class SpecialLeaveApplicationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date_from', 'date_to', 'days_applied', 'credits_used', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'reason']
    date_hierarchy = 'created_at'
    readonly_fields = ['days_applied', 'credits_used', 'created_at', 'updated_at']

@admin.register(SpecialLeaveBalance)
class SpecialLeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'earned', 'used', 'balance', 'year']
    list_filter = ['year']
    search_fields = ['employee__user__first_name', 'employee__user__last_name']
    readonly_fields = ['balance']

@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'year', 'opening_balance', 'carried_forward', 'current_year_entitlement', 'taken', 'balance']
    list_filter = ['leave_type', 'year']
    search_fields = ['employee__user__first_name', 'employee__user__last_name']
    readonly_fields = ['balance']

@admin.register(EmployeeImport)
class EmployeeImportAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'uploaded_by', 'upload_date', 'status', 'total_rows', 'created_count', 'updated_count', 'error_count']
    list_filter = ['status', 'upload_date']
    search_fields = ['file_name', 'uploaded_by__username']
    readonly_fields = ['upload_date', 'total_rows', 'created_count', 'updated_count', 'error_count']

@admin.register(PendingRegistration)
class PendingRegistrationAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'office_location', 'status', 'created_at']
    list_filter = ['status', 'office_location', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['created_at']
    actions = ['approve_registrations', 'reject_registrations']
    
    def approve_registrations(self, request, queryset):
        approved_count = 0
        for registration in queryset.filter(status='pending'):
            try:
                # Create user account
                username = registration.email
                user = User.objects.create_user(
                    username=username,
                    email=registration.email,
                    first_name=registration.first_name,
                    last_name=registration.last_name,
                    password=User.objects.make_random_password()  # Generate random password
                )
                
                # Create employee profile
                employee_id = f"EMP{user.id:04d}"  # Generate employee ID
                Employee.objects.create(
                    user=user,
                    employee_id=employee_id,
                    department="To Be Assigned",
                    position="To Be Assigned",
                    company="Krystal Institute Ltd"
                )
                
                # Update registration status
                registration.status = 'approved'
                registration.reviewed_at = timezone.now()
                registration.reviewed_by = request.user
                registration.save()
                
                approved_count += 1
                
                # Send email notification here (optional)
                # self.send_approval_email(registration, user)
                
            except Exception as e:
                messages.error(request, f"Failed to approve {registration.email}: {str(e)}")
        
        if approved_count > 0:
            messages.success(request, f"Successfully approved {approved_count} registration(s)")
    
    approve_registrations.short_description = "Approve selected registrations"
    
    def reject_registrations(self, request, queryset):
        rejected_count = 0
        for registration in queryset.filter(status='pending'):
            registration.status = 'rejected'
            registration.reviewed_at = timezone.now()
            registration.reviewed_by = request.user
            registration.save()
            rejected_count += 1
        
        if rejected_count > 0:
            messages.success(request, f"Successfully rejected {rejected_count} registration(s)")
    
    reject_registrations.short_description = "Reject selected registrations"