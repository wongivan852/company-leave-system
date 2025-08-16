from django.contrib import admin
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib import messages
from .models import Employee, LeaveType, LeaveApplication, PendingRegistration

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
