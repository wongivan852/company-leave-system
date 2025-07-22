from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, date
import csv
import io
from .forms import LeaveApplicationForm, SpecialWorkClaimForm, SpecialLeaveApplicationForm, BatchApprovalForm
from .models import (EmployeeProfile, LeaveApplication, LeaveBalance, SpecialWorkClaim, 
                    SpecialLeaveApplication, SpecialLeaveNotification, SpecialLeaveApprovalWorkflow)


def create_special_leave_notification(notification_type, recipient, sender=None, work_claim=None, leave_application=None, message=""):
    """Helper function to create special leave notifications"""
    try:
        notification = SpecialLeaveNotification.objects.create(
            notification_type=notification_type,
            recipient=recipient,
            sender=sender,
            work_claim=work_claim,
            leave_application=leave_application,
            message=message
        )
        return notification
    except Exception as e:
        # Log the error but don't break the main workflow
        print(f"Error creating notification: {str(e)}")
        return None


def create_workflow_entry(action, performed_by, work_claim=None, leave_application=None, comment="", old_status="", new_status="", metadata=None):
    """Helper function to create workflow audit trail entries"""
    try:
        workflow_entry = SpecialLeaveApprovalWorkflow.objects.create(
            action=action,
            performed_by=performed_by,
            work_claim=work_claim,
            leave_application=leave_application,
            comment=comment,
            old_status=old_status,
            new_status=new_status,
            metadata=metadata or {}
        )
        return workflow_entry
    except Exception as e:
        # Log the error but don't break the main workflow
        print(f"Error creating workflow entry: {str(e)}")
        return None


def send_notification_email(notification):
    """Helper function to send email notifications (placeholder for future implementation)"""
    # TODO: Implement email sending logic
    # This could integrate with Django's email backend or a service like SendGrid
    try:
        if notification and not notification.email_sent:
            # Placeholder for actual email sending
            # send_mail(subject, message, from_email, [notification.recipient.email])
            
            notification.email_sent = True
            notification.email_sent_at = timezone.now()
            notification.save()
            return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
    return False

@login_required
def apply_leave(request):
    try:
        employee = EmployeeProfile.objects.get(user=request.user)
    except EmployeeProfile.DoesNotExist:
        return render(request, "leave/no_profile.html")

    if request.method == 'POST':
        form = LeaveApplicationForm(request.POST, request.FILES, employee=employee)
        if form.is_valid():
            # Store form data in session for confirmation
            request.session['leave_application_data'] = {
                'leave_type_id': form.cleaned_data['leave_type'].id,
                'start_date': form.cleaned_data['start_date'].isoformat(),
                'start_time': form.cleaned_data['start_time'],
                'end_date': form.cleaned_data['end_date'].isoformat(),
                'end_time': form.cleaned_data['end_time'],
                'reason': form.cleaned_data['reason'],
                'days_applied': float(form.cleaned_data['days_applied']),
                'includes_saturday_work': form.cleaned_data.get('includes_saturday_work', False),
                'saturday_work_days': float(form.cleaned_data.get('saturday_work_days', 0)),
                'saturday_warning': form.cleaned_data.get('saturday_warning', ''),
            }
            
            # Handle file upload separately
            if 'certificate' in request.FILES:
                # For now, we'll handle the file in the confirmation step
                # Store file info in session (you might want to store it temporarily)
                pass
            
            return redirect("leave:apply_leave_confirm")
    else:
        # Check if we have existing data from session (user clicked "Edit")
        application_data = request.session.get('leave_application_data')
        if application_data:
            # Pre-populate form with existing data
            from datetime import datetime
            from .models import LeaveType
            
            try:
                leave_type = LeaveType.objects.get(id=application_data['leave_type_id'])
                
                initial_data = {
                    'leave_type': leave_type,
                    'start_date': datetime.fromisoformat(application_data['start_date']).date(),
                    'start_time': application_data['start_time'],
                    'end_date': datetime.fromisoformat(application_data['end_date']).date(),
                    'end_time': application_data['end_time'],
                    'reason': application_data['reason'],
                }
                
                form = LeaveApplicationForm(employee=employee, initial=initial_data)
                
                # Add a message to indicate this is an edit
                messages.info(request, "You are editing your leave application. Make your changes and submit again.")
            except (LeaveType.DoesNotExist, KeyError, ValueError):
                # If there's any issue with the session data, create fresh form
                form = LeaveApplicationForm(employee=employee)
        else:
            # Fresh form
            form = LeaveApplicationForm(employee=employee)

    # Get holiday information for the sidebar
    holidays = []
    if employee.region:
        try:
            from datetime import datetime
            current_year = datetime.now().year
            holidays_dict = employee.get_holidays_for_region(current_year)
            # Convert to list of tuples for easier template handling
            # holidays_dict.items() returns (date, name) pairs
            holidays = [(name, date) for date, name in holidays_dict.items()]
            # Sort by date and limit to next 10 holidays
            holidays = sorted(holidays, key=lambda x: x[1])[:10]
        except Exception:
            holidays = []

    return render(request, "leave/apply_leave.html", {
        "form": form,
        "employee": employee,
        "profile": employee,
        "holidays": holidays
    })

@login_required
def apply_leave_confirm(request):
    from datetime import datetime, time
    from .models import LeaveType
    
    try:
        employee = EmployeeProfile.objects.get(user=request.user)
    except EmployeeProfile.DoesNotExist:
        return render(request, "leave/no_profile.html")
    
    # Get application data from session (now supports both new applications and revisions)
    application_data = request.session.get('leave_application_data') or request.session.get('application_data')
    if not application_data:
        messages.error(request, "No leave application data found. Please start over.")
        return redirect("leave:apply_leave")
    
    # Check if this is a revision
    is_revision = 'application_id' in application_data
    
    if request.method == 'POST':
        if 'confirm' in request.POST:
            # Handle revision vs new application
            if is_revision:
                # Update existing application
                application = get_object_or_404(LeaveApplication, id=application_data['application_id'], employee__user=request.user)
                
                # Only allow updating pending applications
                if application.status != 'pending':
                    messages.error(request, "You can only revise pending applications.")
                    return redirect('leave:leave_application_detail', application_id=application.id)
                
                # Get leave type
                leave_type = LeaveType.objects.get(name=application_data['leave_type'])
                
                # Convert date and time data back to datetime objects
                start_date = datetime.strptime(application_data['start_date'], '%Y-%m-%d').date()
                end_date = datetime.strptime(application_data['end_date'], '%Y-%m-%d').date()
                
                # Convert time choices to actual times
                start_time_obj = time(9, 0) if application_data['start_time'] == 'AM' else time(13, 0)
                end_time_obj = time(13, 0) if application_data['end_time'] == 'AM' else time(18, 0)
                
                date_from = datetime.combine(start_date, start_time_obj)
                date_to = datetime.combine(end_date, end_time_obj)
                
                # Update the application
                application.leave_type = leave_type
                application.date_from = date_from
                application.date_to = date_to
                application.reason = application_data['reason']
                
                # Recalculate days
                days_applied = application.calculate_leave_days()
                application.days_applied = days_applied
                application.save()
                
                # Clear session data
                if 'application_data' in request.session:
                    del request.session['application_data']
                
                messages.success(request, f'Leave application revised successfully! Duration: {application.days_applied} days. Status: Pending approval.')
                return redirect('leave:leave_application_detail', application_id=application.id)
            
            else:
                # Create new leave application (existing logic)
                leave_type = LeaveType.objects.get(id=application_data['leave_type_id'])
                
                # Convert date and time data back to datetime objects
                start_date = datetime.fromisoformat(application_data['start_date']).date()
                end_date = datetime.fromisoformat(application_data['end_date']).date()
                
                # Convert time choices to actual times
                start_time_obj = time(9, 0) if application_data['start_time'] == 'AM' else time(13, 0)
                end_time_obj = time(13, 0) if application_data['end_time'] == 'AM' else time(18, 0)
                
                date_from = datetime.combine(start_date, start_time_obj)
                date_to = datetime.combine(end_date, end_time_obj)
                
                # Create the leave application
                leave_app = LeaveApplication.objects.create(
                    employee=employee,
                    leave_type=leave_type,
                    date_from=date_from,
                    date_to=date_to,
                    reason=application_data['reason'],
                    days_applied=application_data['days_applied'],
                    includes_saturday_work=application_data['includes_saturday_work'],
                    saturday_work_days=application_data['saturday_work_days']
                )
                
                # Clear session data
                del request.session['leave_application_data']
                
                # Add success message
                success_msg = f'Leave application submitted successfully! Duration: {leave_app.days_applied} days.'
                if leave_app.includes_saturday_work:
                    success_msg += f' (Includes {leave_app.saturday_work_days} Saturday working days as per company policy)'
                success_msg += ' Status: Pending approval.'
                
                messages.success(request, success_msg)
                return redirect("leave:dashboard")
        
        elif 'edit' in request.POST:
            # Redirect back to edit form
            if is_revision:
                return redirect("leave:revise_leave_application", application_id=application_data['application_id'])
            else:
                return redirect("leave:apply_leave")
    
    # Prepare data for display
    if is_revision:
        # For revisions, get leave type by name
        leave_type = LeaveType.objects.get(name=application_data['leave_type'])
        
        # Format dates for display
        start_date_display = datetime.strptime(application_data['start_date'], '%Y-%m-%d').strftime('%B %d, %Y')
        end_date_display = datetime.strptime(application_data['end_date'], '%Y-%m-%d').strftime('%B %d, %Y')
        
        # Calculate days for display (recalculate based on current data)
        start_date = datetime.strptime(application_data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(application_data['end_date'], '%Y-%m-%d').date()
        start_time_obj = time(9, 0) if application_data['start_time'] == 'AM' else time(13, 0)
        end_time_obj = time(13, 0) if application_data['end_time'] == 'AM' else time(18, 0)
        date_from = datetime.combine(start_date, start_time_obj)
        date_to = datetime.combine(end_date, end_time_obj)
        
        # Create a temporary application to calculate days
        temp_app = LeaveApplication(employee=employee, date_from=date_from, date_to=date_to)
        calculated_days = temp_app.calculate_leave_days()
        
        application_data_display = {
            'days_applied': calculated_days,
            'saturday_work_days': 0,  # Will be calculated in the temp calculation
        }
    else:
        # For new applications, use existing logic
        leave_type = LeaveType.objects.get(id=application_data['leave_type_id'])
        
        # Format dates for display
        start_date_display = datetime.fromisoformat(application_data['start_date']).strftime('%B %d, %Y')
        end_date_display = datetime.fromisoformat(application_data['end_date']).strftime('%B %d, %Y')
        
        application_data_display = application_data
    
    # Format times for display
    start_time_display = "9:00 AM" if application_data['start_time'] == 'AM' else "1:00 PM"
    end_time_display = "1:00 PM" if application_data['end_time'] == 'AM' else "6:00 PM"
    
    context = {
        'employee': employee,
        'application_data': application_data_display,
        'leave_type': leave_type,
        'start_date_display': start_date_display,
        'end_date_display': end_date_display,
        'start_time_display': start_time_display,
        'end_time_display': end_time_display,
        'business_days': application_data_display['days_applied'] - application_data_display.get('saturday_work_days', 0),
        'is_revision': is_revision,
    }
    
    return render(request, "leave/apply_leave_confirm.html", context)

@login_required
def leave_applications(request):
    """View for listing leave applications with filtering and pagination"""
    try:
        employee = EmployeeProfile.objects.get(user=request.user)
    except EmployeeProfile.DoesNotExist:
        return render(request, "leave/no_profile.html")
    
    # Get query parameters for filtering
    status_filter = request.GET.get('status', '')
    leave_type_filter = request.GET.get('leave_type', '')
    search = request.GET.get('search', '')
    
    # Base queryset - show all applications if user is staff, otherwise just their own
    if request.user.is_staff:
        applications = LeaveApplication.objects.all()
        is_manager_view = True
    else:
        applications = LeaveApplication.objects.filter(employee=employee)
        is_manager_view = False
    
    # Apply filters
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    if leave_type_filter:
        applications = applications.filter(leave_type__name__icontains=leave_type_filter)
    
    if search:
        applications = applications.filter(
            Q(employee__user__first_name__icontains=search) |
            Q(employee__user__last_name__icontains=search) |
            Q(employee__user__email__icontains=search) |
            Q(reason__icontains=search)
        )
    
    # Order by most recent first
    applications = applications.select_related('employee__user', 'leave_type', 'approver').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(applications, 10)  # Show 10 applications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique leave types for filter dropdown
    from .models import LeaveType
    leave_types = LeaveType.objects.all()
    
    context = {
        'page_obj': page_obj,
        'applications': page_obj,
        'is_manager_view': is_manager_view,
        'status_filter': status_filter,
        'leave_type_filter': leave_type_filter,
        'search': search,
        'leave_types': leave_types,
        'status_choices': LeaveApplication.STATUS_CHOICES,
    }
    
    return render(request, "leave/leave_applications.html", context)

@login_required
def leave_application_detail(request, application_id):
    """View for showing detailed leave application"""
    try:
        employee = EmployeeProfile.objects.get(user=request.user)
    except EmployeeProfile.DoesNotExist:
        return render(request, "leave/no_profile.html")
    
    # Get the application - staff can see all, employees can only see their own
    if request.user.is_staff:
        application = get_object_or_404(LeaveApplication, id=application_id)
    else:
        application = get_object_or_404(LeaveApplication, id=application_id, employee=employee)
    
    # Handle manager approval/rejection
    if request.method == 'POST' and request.user.is_staff:
        action = request.POST.get('action')
        manager_comment = request.POST.get('manager_comment', '')
        
        if action in ['approve', 'reject']:
            application.status = 'approved' if action == 'approve' else 'rejected'
            application.approver = request.user
            application.manager_comment = manager_comment
            application.save()
            
            # Update leave balance if approved
            if action == 'approve':
                try:
                    balance = LeaveBalance.objects.get(
                        employee=application.employee,
                        leave_type=application.leave_type,
                        year=application.date_from.year
                    )
                    balance.save()  # This will recalculate the balance
                except LeaveBalance.DoesNotExist:
                    pass
            
            # Add success message
            status_text = 'approved' if action == 'approve' else 'rejected'
            messages.success(request, f'Leave application #{application.id} has been {status_text} successfully.')
            
            # TODO: Send notification email/SMS here
            return redirect('leave:leave_application_detail', application_id=application_id)
    
    context = {
        'application': application,
        'is_manager_view': request.user.is_staff,
    }
    
    return render(request, "leave/leave_application_detail.html", context)


@login_required
def revise_leave_application(request, application_id):
    """
    Allow users to revise their own pending leave applications
    """
    application = get_object_or_404(LeaveApplication, id=application_id, employee__user=request.user)
    
    # Only allow revision of pending applications
    if application.status != 'pending':
        messages.error(request, "You can only revise pending applications.")
        return redirect('leave:leave_application_detail', application_id=application.id)
    
    if request.method == 'POST':
        form = LeaveApplicationForm(request.POST, instance=application, employee=application.employee)
        if form.is_valid():
            # Clear any existing session data to avoid conflicts
            if 'application_data' in request.session:
                del request.session['application_data']
            if 'leave_application_data' in request.session:
                del request.session['leave_application_data']
                
            # Store form data in session for confirmation
            request.session['application_data'] = {
                'leave_type': form.cleaned_data['leave_type'].name,  # Store name, not object
                'start_date': form.cleaned_data['start_date'].strftime('%Y-%m-%d'),
                'end_date': form.cleaned_data['end_date'].strftime('%Y-%m-%d'),
                'start_time': form.cleaned_data['start_time'],
                'end_time': form.cleaned_data['end_time'],
                'reason': form.cleaned_data['reason'],
                'application_id': application.id  # Store the ID for revision
            }
            return redirect('leave:apply_leave_confirm')
    else:
        # Pre-populate form with existing data
        form = LeaveApplicationForm(instance=application, employee=application.employee)
    
    context = {
        'form': form,
        'application': application,
        'is_revision': True,
    }
    return render(request, "leave/apply_leave.html", context)


@login_required
def withdraw_leave_application(request, application_id):
    """
    Allow users to withdraw their own pending leave applications
    """
    application = get_object_or_404(LeaveApplication, id=application_id, employee__user=request.user)
    
    # Only allow withdrawal of pending applications
    if application.status != 'pending':
        messages.error(request, "You can only withdraw pending applications.")
        return redirect('leave:leave_application_detail', application_id=application.id)
    
    if request.method == 'POST':
        application.status = 'withdrawn'
        application.save()
        messages.success(request, "Your leave application has been withdrawn successfully.")
        return redirect('leave:dashboard')
    
    context = {
        'application': application,
    }
    return render(request, "leave/withdraw_confirmation.html", context)


@login_required
def holiday_management(request):
    """View for managing public holidays"""
    from datetime import datetime
    
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to manage holidays.")
        return redirect('leave:dashboard')
    
    year = request.GET.get('year', datetime.now().year)
    try:
        year = int(year)
    except (ValueError, TypeError):
        year = datetime.now().year
    
    region = request.GET.get('region', 'HK')
    
    from .models import PublicHoliday
    
    # Get holidays for the selected year and region
    holidays = PublicHoliday.objects.filter(
        year=year,
        region=region
    ).order_by('date')
    
    # If no holidays exist for this year/region, import them
    if not holidays.exists():
        try:
            from .models import EmployeeProfile
            # Use the first employee's method to import holidays
            emp = EmployeeProfile.objects.filter(region=region).first()
            if emp:
                emp.get_holidays_for_region(year)
                holidays = PublicHoliday.objects.filter(year=year, region=region).order_by('date')
        except Exception:
            pass
    
    context = {
        'holidays': holidays,
        'current_year': year,
        'current_region': region,
        'regions': PublicHoliday.REGION_CHOICES,
        'years': range(year - 2, year + 3),
    }
    
    return render(request, "leave/holiday_management.html", context)


@login_required
def holiday_import(request):
    """Import holidays for a specific year and region"""
    from datetime import datetime
    
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to import holidays.")
        return redirect('leave:dashboard')
    
    if request.method == 'POST':
        year = int(request.POST.get('year', datetime.now().year))
        region = request.POST.get('region', 'HK')
        
        try:
            from .models import PublicHoliday
            import holidays
            
            # Delete existing holidays for this year/region if re-importing
            if request.POST.get('overwrite') == 'true':
                PublicHoliday.objects.filter(year=year, region=region, is_imported=True).delete()
            
            if region == 'HK':
                region_holidays = holidays.HongKong(years=year)
            elif region == 'CN':
                region_holidays = holidays.China(years=year)
            else:
                messages.error(request, "Invalid region selected.")
                return redirect('leave:holiday_management')
            
            imported_count = 0
            for date, name in region_holidays.items():
                holiday, created = PublicHoliday.objects.get_or_create(
                    date=date,
                    region=region,
                    defaults={
                        'name': name,
                        'year': date.year,
                        'is_active': True,
                        'is_imported': True
                    }
                )
                if created:
                    imported_count += 1
            
            messages.success(request, f"Imported {imported_count} holidays for {region} {year}")
            
        except Exception as e:
            messages.error(request, f"Error importing holidays: {str(e)}")
    
    return redirect('leave:holiday_management')


@login_required
def holiday_add(request):
    """Add a custom holiday"""
    from datetime import datetime
    
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to add holidays.")
        return redirect('leave:dashboard')
    
    if request.method == 'POST':
        try:
            from .models import PublicHoliday
            
            name = request.POST.get('name', '').strip()
            date_str = request.POST.get('date', '')
            region = request.POST.get('region', 'HK')
            
            if not name:
                messages.error(request, "Holiday name is required.")
                return redirect('leave:holiday_management')
            
            if not date_str:
                messages.error(request, "Holiday date is required.")
                return redirect('leave:holiday_management')
            
            # Parse the date
            holiday_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Check if holiday already exists
            if PublicHoliday.objects.filter(date=holiday_date, region=region).exists():
                messages.error(request, f"A holiday already exists on {holiday_date} for {region}.")
                return redirect('leave:holiday_management')
            
            # Create the holiday
            PublicHoliday.objects.create(
                name=name,
                date=holiday_date,
                region=region,
                year=holiday_date.year,
                is_active=True,
                is_imported=False  # This is a custom holiday
            )
            
            messages.success(request, f"Holiday '{name}' added successfully for {holiday_date}.")
            
        except ValueError:
            messages.error(request, "Invalid date format.")
        except Exception as e:
            messages.error(request, f"Error adding holiday: {str(e)}")
    
    return redirect('leave:holiday_management')


@login_required
def employee_import(request):
    """Import employee data from CSV/Excel file"""
    from datetime import datetime
    import csv
    import io
    
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to import employee data.")
        return redirect('leave:dashboard')
    
    if request.method == 'POST':
        import_record = None
        try:
            from django.contrib.auth.models import User
            from .models import EmployeeProfile, LeaveType, LeaveBalance, EmployeeImportRecord
            
            uploaded_file = request.FILES.get('employee_file')
            if not uploaded_file:
                messages.error(request, "Please select a file to upload.")
                return redirect('leave:holiday_management')
            
            # Check file type
            if not uploaded_file.name.endswith('.csv'):
                messages.error(request, "Please upload a CSV file.")
                return redirect('leave:holiday_management')
            
            # Read file content
            file_data = uploaded_file.read().decode('utf-8')
            
            # Create import record
            import_record = EmployeeImportRecord.objects.create(
                uploaded_by=request.user,
                file_name=uploaded_file.name,
                file_content=file_data,
                status='failed'  # Will update this based on results
            )
            
            csv_reader = csv.DictReader(io.StringIO(file_data))
            
            created_count = 0
            updated_count = 0
            error_count = 0
            total_rows = 0
            import_log = []
            
            for row_num, row in enumerate(csv_reader, start=2):  # Start from 2 to account for header
                total_rows += 1
                try:
                    # Required fields
                    username = row.get('username', '').strip()
                    email = row.get('email', '').strip()
                    first_name = row.get('first_name', '').strip()
                    last_name = row.get('last_name', '').strip()
                    date_joined = row.get('date_joined', '').strip()
                    region = row.get('region', 'HK').strip()
                    
                    # Optional fields
                    is_staff = row.get('is_staff', 'False').strip().lower() in ('true', '1', 'yes')
                    annual_leave_balance = row.get('annual_leave_balance', '0').strip()
                    sick_leave_balance = row.get('sick_leave_balance', '0').strip()
                    
                    if not all([username, email, first_name, last_name, date_joined]):
                        error_msg = f"Row {row_num}: Missing required fields"
                        import_log.append(error_msg)
                        error_count += 1
                        continue
                    
                    # Parse date
                    try:
                        join_date = datetime.strptime(date_joined, '%Y-%m-%d').date()
                    except ValueError:
                        try:
                            join_date = datetime.strptime(date_joined, '%d/%m/%Y').date()
                        except ValueError:
                            error_msg = f"Row {row_num}: Invalid date format. Use YYYY-MM-DD or DD/MM/YYYY"
                            import_log.append(error_msg)
                            error_count += 1
                            continue
                    
                    # Create or update user
                    user, user_created = User.objects.get_or_create(
                        username=username,
                        defaults={
                            'email': email,
                            'first_name': first_name,
                            'last_name': last_name,
                            'is_staff': is_staff
                        }
                    )
                    
                    if not user_created:
                        # Update existing user
                        user.email = email
                        user.first_name = first_name
                        user.last_name = last_name
                        user.is_staff = is_staff
                        user.save()
                        updated_count += 1
                        import_log.append(f"Row {row_num}: Updated user {username}")
                    else:
                        created_count += 1
                        import_log.append(f"Row {row_num}: Created user {username}")
                    
                    # Create or update employee profile
                    profile, profile_created = EmployeeProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'date_joined': join_date,
                            'region': region if region in ['HK', 'CN'] else 'HK'
                        }
                    )
                    
                    if not profile_created:
                        profile.date_joined = join_date
                        profile.region = region if region in ['HK', 'CN'] else 'HK'
                        profile.save()
                    
                    # Create leave balances if provided
                    current_year = datetime.now().year
                    
                    if annual_leave_balance and float(annual_leave_balance) > 0:
                        try:
                            annual_leave_type = LeaveType.objects.get(name='Annual Leave')
                            balance, _ = LeaveBalance.objects.get_or_create(
                                employee=profile,
                                leave_type=annual_leave_type,
                                year=current_year,
                                defaults={
                                    'balance': float(annual_leave_balance),
                                    'taken': 0
                                }
                            )
                            if not _:  # Update existing balance
                                balance.balance = float(annual_leave_balance)
                                balance.save()
                            import_log.append(f"  - Set annual leave balance: {annual_leave_balance}")
                        except (LeaveType.DoesNotExist, ValueError):
                            import_log.append(f"  - Warning: Could not set annual leave balance")
                    
                    if sick_leave_balance and float(sick_leave_balance) > 0:
                        try:
                            sick_leave_type = LeaveType.objects.get(name='Sick Leave')
                            balance, _ = LeaveBalance.objects.get_or_create(
                                employee=profile,
                                leave_type=sick_leave_type,
                                year=current_year,
                                defaults={
                                    'balance': float(sick_leave_balance),
                                    'taken': 0
                                }
                            )
                            if not _:  # Update existing balance
                                balance.balance = float(sick_leave_balance)
                                balance.save()
                            import_log.append(f"  - Set sick leave balance: {sick_leave_balance}")
                        except (LeaveType.DoesNotExist, ValueError):
                            import_log.append(f"  - Warning: Could not set sick leave balance")
                            
                except Exception as e:
                    error_msg = f"Row {row_num}: Error processing - {str(e)}"
                    import_log.append(error_msg)
                    error_count += 1
                    continue
            
            # Update import record with results
            if error_count == 0:
                status = 'success'
            elif error_count < total_rows:
                status = 'partial'
            else:
                status = 'failed'
            
            import_record.total_rows = total_rows
            import_record.created_count = created_count
            import_record.updated_count = updated_count
            import_record.error_count = error_count
            import_record.status = status
            import_record.import_log = '\n'.join(import_log)
            import_record.save()
            
            # Summary message
            success_msg = []
            if created_count > 0:
                success_msg.append(f"{created_count} employees created")
            if updated_count > 0:
                success_msg.append(f"{updated_count} employees updated")
            
            if success_msg:
                messages.success(request, f"Import completed: {', '.join(success_msg)}")
            
            if error_count > 0:
                messages.warning(request, f"{error_count} rows had errors. Check import history for details.")
                
        except Exception as e:
            if import_record:
                import_record.status = 'failed'
                import_record.import_log = f"Fatal error: {str(e)}"
                import_record.save()
            messages.error(request, f"Error importing employee data: {str(e)}")
    
    return redirect('leave:holiday_management')


@login_required 
def holiday_edit(request, holiday_id):
    """Edit a specific holiday"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to edit holidays.")
        return redirect('leave:dashboard')
    
    from .models import PublicHoliday
    holiday = get_object_or_404(PublicHoliday, id=holiday_id)
    
    if request.method == 'POST':
        holiday.name = request.POST.get('name', holiday.name)
        holiday.is_active = request.POST.get('is_active') == 'on'
        holiday.save()
        messages.success(request, f"Holiday '{holiday.name}' updated successfully.")
        return redirect('leave:holiday_management')
    
    context = {
        'holiday': holiday,
    }
    return render(request, "leave/holiday_edit.html", context)


@login_required
def holiday_delete(request, holiday_id):
    """Delete a specific holiday"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to delete holidays.")
        return redirect('leave:dashboard')
    
    from .models import PublicHoliday
    holiday = get_object_or_404(PublicHoliday, id=holiday_id)
    
    if request.method == 'POST':
        holiday_name = holiday.name
        holiday.delete()
        messages.success(request, f"Holiday '{holiday_name}' deleted successfully.")
    
    return redirect('leave:holiday_management')


@login_required
def import_history(request):
    """Display import history for managers"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to view import history.")
        return redirect('leave:dashboard')
    
    from .models import EmployeeImportRecord
    imports = EmployeeImportRecord.objects.all().order_by('-upload_date')
    
    return render(request, 'leave/import_history.html', {
        'imports': imports
    })


@login_required
def view_import_content(request, import_id):
    """View the content of a specific import"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to view import content.")
        return redirect('leave:dashboard')
    
    from .models import EmployeeImportRecord
    from django.http import HttpResponse
    
    try:
        import_record = EmployeeImportRecord.objects.get(id=import_id)
        
        # Return CSV content as downloadable file
        response = HttpResponse(import_record.file_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{import_record.file_name}"'
        return response
        
    except EmployeeImportRecord.DoesNotExist:
        messages.error(request, "Import record not found.")
        return redirect('leave:import_history')


@login_required
def download_balances(request):
    """Download leave balances as of a specific date"""
    # Check if user is staff (manager)
    if not request.user.is_staff:
        messages.error(request, "Access denied. Only managers can download balance reports.")
        return redirect('leave:dashboard')
    
    if request.method == 'POST':
        as_of_date_str = request.POST.get('as_of_date')
        region_filter = request.POST.get('region_filter', '')
        format_type = request.POST.get('format', 'csv')
        
        try:
            as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, "Invalid date format.")
            return redirect('leave:dashboard')
        
        # Get all employees
        employees = EmployeeProfile.objects.all()
        
        # Apply region filter if specified
        if region_filter:
            employees = employees.filter(region=region_filter)
        
        # Prepare data
        balance_data = []
        
        for employee in employees:
            user = employee.user
            
            # Calculate balances as of the specified date
            annual_balance = 0
            sick_balance = 0
            annual_taken = 0
            sick_taken = 0
            annual_entitlement = 0
            sick_entitlement = 0
            
            try:
                # Get leave balances for the year of as_of_date
                year = as_of_date.year
                balances = LeaveBalance.objects.filter(employee=employee, year=year)
                
                for balance in balances:
                    if balance.leave_type.name == 'Annual Leave':
                        annual_entitlement = float(balance.current_year_entitlement)
                        # Calculate taken up to as_of_date
                        taken_applications = LeaveApplication.objects.filter(
                            employee=employee,
                            leave_type=balance.leave_type,
                            status='approved',
                            date_from__lte=as_of_date,
                            date_from__year=year
                        )
                        annual_taken = sum(float(app.days_applied) for app in taken_applications)
                        annual_balance = annual_entitlement - annual_taken
                        
                    elif balance.leave_type.name == 'Sick Leave':
                        sick_entitlement = float(balance.current_year_entitlement)
                        # Calculate taken up to as_of_date
                        taken_applications = LeaveApplication.objects.filter(
                            employee=employee,
                            leave_type=balance.leave_type,
                            status='approved',
                            date_from__lte=as_of_date,
                            date_from__year=year
                        )
                        sick_taken = sum(float(app.days_applied) for app in taken_applications)
                        sick_balance = sick_entitlement - sick_taken
                        
            except Exception as e:
                # If any error, set to 0
                pass
            
            balance_data.append({
                'employee_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                'email': user.email,
                'region': employee.get_region_display(),
                'date_joined': employee.date_joined.strftime('%Y-%m-%d'),
                'annual_entitlement': annual_entitlement,
                'annual_taken': annual_taken,
                'annual_balance': annual_balance,
                'sick_entitlement': sick_entitlement,
                'sick_taken': sick_taken,
                'sick_balance': sick_balance,
            })
        
        # Generate filename
        region_text = f"_{region_filter}" if region_filter else "_All"
        filename = f"leave_balances_{as_of_date.strftime('%Y%m%d')}{region_text}"
        
        if format_type == 'excel':
            # Excel format
            try:
                import openpyxl
                from openpyxl.utils.dataframe import dataframe_to_rows
                import pandas as pd
                
                # Create DataFrame
                df = pd.DataFrame(balance_data)
                df.columns = [
                    'Employee Name', 'Email', 'Region', 'Date Joined',
                    'Annual Entitlement', 'Annual Taken', 'Annual Balance',
                    'Sick Entitlement', 'Sick Taken', 'Sick Balance'
                ]
                
                # Create Excel file
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Leave Balances', index=False)
                    
                    # Auto-adjust column widths
                    worksheet = writer.sheets['Leave Balances']
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                
                output.seek(0)
                response = HttpResponse(
                    output.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
                return response
                
            except ImportError:
                # If pandas/openpyxl not available, fall back to CSV
                messages.warning(request, "Excel export not available. Downloading as CSV instead.")
                format_type = 'csv'
        
        if format_type == 'csv':
            # CSV format
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            
            writer = csv.writer(response)
            
            # Write header
            writer.writerow([
                'Employee Name', 'Email', 'Region', 'Date Joined',
                'Annual Entitlement', 'Annual Taken', 'Annual Balance',
                'Sick Entitlement', 'Sick Taken', 'Sick Balance'
            ])
            
            # Write data
            for data in balance_data:
                writer.writerow([
                    data['employee_name'],
                    data['email'],
                    data['region'],
                    data['date_joined'],
                    data['annual_entitlement'],
                    data['annual_taken'],
                    data['annual_balance'],
                    data['sick_entitlement'],
                    data['sick_taken'],
                    data['sick_balance'],
                ])
            
            return response
        
    # If GET request, redirect to dashboard
    return redirect('leave:dashboard')


@login_required
def special_work_claim(request):
    """View for employees to claim special leave credits for working beyond normal hours"""
    try:
        employee = EmployeeProfile.objects.get(user=request.user)
    except EmployeeProfile.DoesNotExist:
        return render(request, "leave/no_profile.html")

    if request.method == 'POST':
        form = SpecialWorkClaimForm(request.POST, employee=employee)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.employee = employee
            claim.save()
            
            # Create workflow entry
            create_workflow_entry(
                action='submitted',
                performed_by=request.user,
                work_claim=claim,
                comment=f"Work claim submitted for {claim.event_name}"
            )
            
            # Create notification for managers (staff users)
            staff_users = User.objects.filter(is_staff=True, is_active=True)
            for manager in staff_users:
                create_special_leave_notification(
                    notification_type='claim_submitted',
                    recipient=manager,
                    sender=request.user,
                    work_claim=claim,
                    message=f"{employee.user.get_full_name()} submitted a work claim for {claim.event_name} on {claim.work_date}"
                )
            
            credits_text = "0.5 credit" if claim.session in ['AM', 'PM'] else "1.0 credit"
            priority_text = f" (Priority: {claim.get_priority_display()})" if claim.priority != 'normal' else ""
            
            messages.success(
                request, 
                f"Special work claim submitted successfully! You will earn {credits_text} once approved by your manager.{priority_text}"
            )
            return redirect('leave:special_work_claim')
    else:
        form = SpecialWorkClaimForm(employee=employee)

    # Get existing claims for this employee
    claims = SpecialWorkClaim.objects.filter(employee=employee).order_by('-work_date', '-created_at')
    
    # Paginate claims
    paginator = Paginator(claims, 10)
    page_number = request.GET.get('page')
    page_claims = paginator.get_page(page_number)

    # Get special leave balance
    balance_info = employee.get_special_leave_balance()
    
    # Get pending counts for employee awareness
    pending_claims_count = claims.filter(status='pending').count()
    approved_claims_count = claims.filter(status='approved').count()

    context = {
        'form': form,
        'claims': page_claims,
        'balance_info': balance_info,
        'employee': employee,
        'pending_claims_count': pending_claims_count,
        'approved_claims_count': approved_claims_count,
    }
    
    return render(request, 'leave/special_work_claim.html', context)


@login_required
def special_leave_apply(request):
    """View for employees to apply for special leave using earned credits"""
    try:
        employee = EmployeeProfile.objects.get(user=request.user)
    except EmployeeProfile.DoesNotExist:
        return render(request, "leave/no_profile.html")

    # Get special leave balance
    balance_info = employee.get_special_leave_balance()
    
    # Check if employee has any balance
    if balance_info['balance'] <= 0:
        messages.warning(
            request, 
            "You don't have any special leave credits. Please submit work claims for approval first."
        )
        return redirect('leave:special_work_claim')

    if request.method == 'POST':
        form = SpecialLeaveApplicationForm(request.POST, employee=employee)
        if form.is_valid():
            application = form.save(commit=False)
            application.employee = employee
            application.save()
            
            # Create workflow entry
            create_workflow_entry(
                action='submitted',
                performed_by=request.user,
                leave_application=application,
                comment=f"Special leave application submitted for {application.leave_date}"
            )
            
            # Create notification for managers
            staff_users = User.objects.filter(is_staff=True, is_active=True)
            notification_type = 'urgent_approval_needed' if application.urgency == 'urgent' else 'application_submitted'
            
            for manager in staff_users:
                urgency_text = f" (URGENT)" if application.urgency == 'urgent' else ""
                create_special_leave_notification(
                    notification_type=notification_type,
                    recipient=manager,
                    sender=request.user,
                    leave_application=application,
                    message=f"{employee.user.get_full_name()} applied for special leave on {application.leave_date}{urgency_text}"
                )
            
            credits_text = "0.5 credit" if application.session in ['AM', 'PM'] else "1.0 credit"
            urgency_text = f" (Urgency: {application.get_urgency_display()})" if application.urgency != 'normal' else ""
            
            messages.success(
                request, 
                f"Special leave application submitted successfully! {credits_text} will be deducted once approved.{urgency_text}"
            )
            return redirect('leave:special_leave_apply')
    else:
        form = SpecialLeaveApplicationForm(employee=employee)

    # Get existing applications for this employee
    applications = SpecialLeaveApplication.objects.filter(employee=employee).order_by('-leave_date', '-created_at')
    
    # Paginate applications
    paginator = Paginator(applications, 10)
    page_number = request.GET.get('page')
    page_applications = paginator.get_page(page_number)
    
    # Get application statistics
    pending_applications_count = applications.filter(status='pending').count()
    approved_applications_count = applications.filter(status='approved').count()
    urgent_applications_count = applications.filter(urgency='urgent', status='pending').count()

    context = {
        'form': form,
        'applications': page_applications,
        'balance_info': balance_info,
        'employee': employee,
        'pending_applications_count': pending_applications_count,
        'approved_applications_count': approved_applications_count,
        'urgent_applications_count': urgent_applications_count,
    }
    
    return render(request, 'leave/special_leave_apply.html', context)


@login_required
def special_leave_management(request):
    """Enhanced view for managers to approve/reject special work claims and leave applications"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('leave:dashboard')

    # Handle approval/rejection actions (both individual and batch)
    if request.method == 'POST':
        # Check if this is a batch action
        if 'batch_action' in request.POST:
            batch_form = BatchApprovalForm(request.POST)
            if batch_form.is_valid():
                action = batch_form.cleaned_data['action']
                comment = batch_form.cleaned_data['comment']
                selected_claims = batch_form.cleaned_data.get('selected_claims', '').split(',')
                selected_applications = batch_form.cleaned_data.get('selected_applications', '').split(',')
                
                processed_count = 0
                
                # Process selected claims
                if selected_claims and selected_claims[0]:  # Check if not empty
                    for claim_id in selected_claims:
                        try:
                            claim = SpecialWorkClaim.objects.get(id=claim_id.strip(), status='pending')
                            old_status = claim.status
                            claim.status = 'approved' if action == 'approve' else 'rejected'
                            claim.approver = request.user
                            claim.manager_comment = comment
                            if action == 'reject':
                                claim.rejection_reason = comment
                            claim.save()
                            
                            # Create workflow entry
                            create_workflow_entry(
                                action=action,
                                performed_by=request.user,
                                work_claim=claim,
                                comment=comment,
                                old_status=old_status,
                                new_status=claim.status
                            )
                            
                            # Create notification for employee
                            notification_type = 'claim_approved' if action == 'approve' else 'claim_rejected'
                            create_special_leave_notification(
                                notification_type=notification_type,
                                recipient=claim.employee.user,
                                sender=request.user,
                                work_claim=claim,
                                message=f"Your work claim for {claim.event_name} has been {action}d by {request.user.get_full_name()}"
                            )
                            
                            processed_count += 1
                        except SpecialWorkClaim.DoesNotExist:
                            continue
                
                # Process selected applications
                if selected_applications and selected_applications[0]:  # Check if not empty
                    for app_id in selected_applications:
                        try:
                            application = SpecialLeaveApplication.objects.get(id=app_id.strip(), status='pending')
                            old_status = application.status
                            application.status = 'approved' if action == 'approve' else 'rejected'
                            application.approver = request.user
                            application.manager_comment = comment
                            if action == 'reject':
                                application.rejection_reason = comment
                            application.save()
                            
                            # Create workflow entry
                            create_workflow_entry(
                                action=action,
                                performed_by=request.user,
                                leave_application=application,
                                comment=comment,
                                old_status=old_status,
                                new_status=application.status
                            )
                            
                            # Create notification for employee
                            notification_type = 'application_approved' if action == 'approve' else 'application_rejected'
                            create_special_leave_notification(
                                notification_type=notification_type,
                                recipient=application.employee.user,
                                sender=request.user,
                                leave_application=application,
                                message=f"Your special leave application for {application.leave_date} has been {action}d by {request.user.get_full_name()}"
                            )
                            
                            processed_count += 1
                        except SpecialLeaveApplication.DoesNotExist:
                            continue
                
                if processed_count > 0:
                    action_text = 'approved' if action == 'approve' else 'rejected'
                    messages.success(request, f"Successfully {action_text} {processed_count} item(s).")
                else:
                    messages.warning(request, "No valid items were processed.")
                    
        else:
            # Handle individual actions (existing logic)
            action = request.POST.get('action')
            item_type = request.POST.get('type')  # 'claim' or 'application'
            item_id = request.POST.get('id')
            comment = request.POST.get('manager_comment', '')

            if action in ['approve', 'reject'] and item_type and item_id:
                try:
                    if item_type == 'claim':
                        item = SpecialWorkClaim.objects.get(id=item_id)
                        item_name = f"work claim for {item.event_name}"
                    elif item_type == 'application':
                        item = SpecialLeaveApplication.objects.get(id=item_id)
                        item_name = f"leave application for {item.leave_date}"
                    else:
                        raise ValueError("Invalid item type")

                    # Update status
                    old_status = item.status
                    item.status = 'approved' if action == 'approve' else 'rejected'
                    item.approver = request.user
                    item.manager_comment = comment
                    if action == 'reject':
                        item.rejection_reason = comment
                    item.save()
                    
                    # Create workflow entry
                    create_workflow_entry(
                        action=action,
                        performed_by=request.user,
                        work_claim=item if item_type == 'claim' else None,
                        leave_application=item if item_type == 'application' else None,
                        comment=comment,
                        old_status=old_status,
                        new_status=item.status
                    )
                    
                    # Create notification for employee
                    if item_type == 'claim':
                        notification_type = 'claim_approved' if action == 'approve' else 'claim_rejected'
                    else:
                        notification_type = 'application_approved' if action == 'approve' else 'application_rejected'
                    
                    create_special_leave_notification(
                        notification_type=notification_type,
                        recipient=item.employee.user,
                        sender=request.user,
                        work_claim=item if item_type == 'claim' else None,
                        leave_application=item if item_type == 'application' else None,
                        message=f"Your {item_name} has been {action}d by {request.user.get_full_name()}"
                    )

                    action_text = 'approved' if action == 'approve' else 'rejected'
                    messages.success(
                        request, 
                        f"Successfully {action_text} {item.employee.user.get_full_name()}'s {item_name}."
                    )

                except (SpecialWorkClaim.DoesNotExist, SpecialLeaveApplication.DoesNotExist):
                    messages.error(request, "Item not found.")
                except Exception as e:
                    messages.error(request, f"Error processing request: {str(e)}")

        return redirect('leave:special_leave_management')

    # Get pending items with enhanced filtering
    pending_claims = SpecialWorkClaim.objects.filter(status='pending').order_by('priority', '-work_date')
    pending_applications = SpecialLeaveApplication.objects.filter(status='pending').order_by('urgency', 'leave_date')
    
    # Separate urgent items for priority handling
    urgent_applications = pending_applications.filter(urgency='urgent')
    high_priority_claims = pending_claims.filter(priority='high')

    # Get recent processed items for reference
    recent_claims = SpecialWorkClaim.objects.filter(
        status__in=['approved', 'rejected']
    ).order_by('-updated_at')[:5]
    
    recent_applications = SpecialLeaveApplication.objects.filter(
        status__in=['approved', 'rejected']
    ).order_by('-updated_at')[:5]
    
    # Create batch form
    batch_form = BatchApprovalForm()

    context = {
        'pending_claims': pending_claims,
        'pending_applications': pending_applications,
        'urgent_applications': urgent_applications,
        'high_priority_claims': high_priority_claims,
        'recent_claims': recent_claims,
        'recent_applications': recent_applications,
        'batch_form': batch_form,
    }
    
    return render(request, 'leave/special_leave_management.html', context)