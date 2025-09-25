from datetime import datetime, timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import get_template
# weasyprint will be imported dynamically when needed
from .models import LeaveApplication, LeaveType, Employee, SpecialWorkClaim, SpecialLeaveApplication, SpecialLeaveBalance, EmployeeImport, LeaveBalance
from .forms import LeaveApplicationForm, SpecialWorkClaimForm, SpecialLeaveApplicationForm, EmployeeImportForm
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
import csv
import io
from decimal import Decimal
from django.db import transaction
from django.http import JsonResponse

def is_manager(user):
    """Check if user is admin or magneoh (managers)"""
    return user.is_authenticated and (user.username in ['admin', 'magneoh'] or user.is_superuser)

def is_staff_or_manager(user):
    """Check if user is staff or manager"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)

def calculate_return_date(date_to):
    """Calculate the return to work date based on the leave end date."""
    # For half-day leaves ending at 1:00pm (13:00), return to work same day at 2:00pm
    if date_to.hour == 13:
        return date_to.date()
    
    # For morning leaves ending before 1:00pm, return same day afternoon
    if date_to.hour < 13:
        return date_to.date()
    
    # If leave ends in the afternoon (after 1:00pm), return next working day morning
    next_day = date_to.date() + timedelta(days=1)
    
    # Skip weekends
    while next_day.weekday() in [5, 6]:  # 5=Saturday, 6=Sunday
        next_day += timedelta(days=1)
        
    return next_day

class LeaveApplicationListView(LoginRequiredMixin, ListView):
    model = LeaveApplication
    template_name = 'leave/leave_application_list.html'
    context_object_name = 'leave_applications'
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'employee'):
            if user.is_staff:
                return LeaveApplication.objects.all().order_by('-created_at')
            else:
                return LeaveApplication.objects.filter(employee=user.employee).order_by('-created_at')
        return LeaveApplication.objects.none()

class LeaveApplicationDetailView(LoginRequiredMixin, DetailView):
    model = LeaveApplication
    template_name = 'leave/leave_application_detail.html'
    context_object_name = 'leave_application'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_object()
        date_back = calculate_return_date(application.date_to)
        context['date_back_to_work'] = date_back
        return context

@login_required
def leave_form_print(request, application_id):
    application = get_object_or_404(LeaveApplication, pk=application_id)
    date_back = calculate_return_date(application.date_to)
    
    context = {
        'application': application,
        'date_back_to_work': date_back,
        'is_pdf': False
    }
    
    return render(request, 'leave/leave_form_print.html', context)

@login_required
def leave_form_pdf(request, application_id):
    application = get_object_or_404(LeaveApplication, pk=application_id)
    date_back = calculate_return_date(application.date_to)
    
    template = get_template('leave/leave_form_print.html')
    context = {
        'application': application,
        'date_back_to_work': date_back,
        'is_pdf': True
    }
    html = template.render(context)
    
    try:
        # Try to generate PDF using weasyprint if available
        import weasyprint
        pdf_file = weasyprint.HTML(string=html).write_pdf()
        
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="leave_application_{application.employee.user.get_full_name().replace(" ", "_")}_{application_id}.pdf"'
        
        return response
    except ImportError:
        # If weasyprint is not available, redirect to print view
        from django.contrib import messages
        messages.warning(request, 'PDF generation is not available. Please use the print function instead.')
        return redirect('leave:leave_form_print', application_id=application_id)

# Placeholder views to prevent URL errors
@login_required
def apply_leave(request):
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return render(request, "leave/no_profile.html")
    
    if request.method == 'POST':
        form = LeaveApplicationForm(request.POST, employee=employee)
        if form.is_valid():
            application = form.save(commit=False)
            application.employee = employee
            application.save()
            
            messages.success(request, 'Leave application submitted successfully!')
            return redirect('leave:apply_leave_confirm', application_id=application.id)
    else:
        form = LeaveApplicationForm(employee=employee)
    
    return render(request, 'leave/apply_leave.html', {
        'form': form,
        'employee': employee,
        'is_revision': False
    })

@login_required
def apply_leave_confirm(request, application_id):
    application = get_object_or_404(LeaveApplication, pk=application_id, employee__user=request.user)
    
    if request.method == 'POST':
        if 'confirm' in request.POST:
            # Application is already saved, just redirect to applications list
            messages.success(request, 'Leave application confirmed!')
            return redirect('leave:leave_applications')
        elif 'edit' in request.POST:
            # Redirect back to apply form with this application
            return redirect('leave:apply_leave')  # Could be enhanced to pass application data for editing
    
    # Prepare context data for template
    context = {
        'employee': application.employee,
        'leave_type': application.leave_type,
        'application_data': {
            'days_applied': application.days_applied,
            'reason': application.reason,
        },
        'start_date_display': application.date_from.strftime('%A, %B %d, %Y'),
        'start_time_display': 'AM (9:00am - 1:00pm)' if application.date_from.hour == 9 else 'PM (2:00pm - 6:00pm)',
        'end_date_display': application.date_to.strftime('%A, %B %d, %Y'),
        'end_time_display': 'AM (9:00am - 1:00pm)' if application.date_to.hour == 13 else 'PM (2:00pm - 6:00pm)',
        'is_revision': False
    }
    
    return render(request, 'leave/apply_leave_confirm.html', context)

@login_required
def leave_applications(request):
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return render(request, "leave/no_profile.html")
    
    # Check if user is a manager
    user_is_manager = is_manager(request.user)
    
    # If user is a manager (admin, magneoh, or superuser), show all applications
    if user_is_manager:
        applications = LeaveApplication.objects.all().order_by('-created_at')
    else:
        # Regular employees see only their own applications
        applications = LeaveApplication.objects.filter(employee=employee).order_by('-created_at')
    
    # Add pagination
    from django.core.paginator import Paginator
    paginator = Paginator(applications, 25)  # Show 25 applications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get leave types for filter dropdown
    from .models import LeaveType
    leave_types = LeaveType.objects.all()
    
    # Status choices for filter
    status_choices = [
        ('pending', 'Pending'),
        ('approved', 'Approved'), 
        ('rejected', 'Rejected'),
    ]
    
    return render(request, 'leave/leave_applications.html', {
        'applications': page_obj,
        'page_obj': page_obj,
        'employee': employee,
        'is_manager_view': user_is_manager,
        'leave_types': leave_types,
        'status_choices': status_choices,
        'status_filter': request.GET.get('status', ''),
        'leave_type_filter': request.GET.get('leave_type', ''),
        'search': request.GET.get('search', ''),
    })

@login_required
def leave_application_detail(request, application_id):
    application = get_object_or_404(LeaveApplication, pk=application_id)
    return render(request, 'leave/leave_application_detail.html', {'application': application})

@login_required
def revise_leave_application(request, application_id):
    return render(request, 'leave/revise_leave.html', {'message': 'Feature coming soon'})

@login_required
def withdraw_leave_application(request, application_id):
    return render(request, 'leave/withdraw_leave.html', {'message': 'Feature coming soon'})

@login_required
def holiday_management(request):
    return render(request, 'leave/holiday_management.html', {'message': 'Feature coming soon'})

@login_required
def holiday_import(request):
    return render(request, 'leave/holiday_import.html', {'message': 'Feature coming soon'})

@login_required
def holiday_add(request):
    return render(request, 'leave/holiday_add.html', {'message': 'Feature coming soon'})

@login_required
@user_passes_test(is_staff_or_manager)
def employee_import(request):
    """Handle employee CSV import functionality"""
    if request.method == 'POST':
        form = EmployeeImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            
            # Create import record
            import_record = EmployeeImport.objects.create(
                file_name=csv_file.name,
                uploaded_by=request.user,
                status='processing'
            )
            
            try:
                # Process the CSV file
                result = process_employee_csv(csv_file, import_record, request.user)
                
                # Update import record with results
                import_record.status = result['status']
                import_record.total_rows = result['total_rows']
                import_record.created_count = result['created_count']
                import_record.updated_count = result['updated_count']
                import_record.error_count = result['error_count']
                import_record.import_log = result['log']
                import_record.csv_content = result['csv_content']
                import_record.save()
                
                if result['status'] == 'success':
                    messages.success(request, f"Successfully imported {result['created_count']} employees and updated {result['updated_count']} employees.")
                elif result['status'] == 'partial':
                    messages.warning(request, f"Import completed with some errors. {result['created_count']} created, {result['updated_count']} updated, {result['error_count']} errors.")
                else:
                    messages.error(request, f"Import failed. Check the import history for details.")
                
                return redirect('leave:import_history')
                
            except Exception as e:
                import_record.status = 'failed'
                import_record.import_log = f"Fatal error during import: {str(e)}"
                import_record.save()
                messages.error(request, f"Import failed: {str(e)}")
                
    else:
        form = EmployeeImportForm()
    
    return render(request, 'leave/employee_import.html', {'form': form})

@login_required
@user_passes_test(is_staff_or_manager)
def import_history(request):
    """Display import history"""
    imports = EmployeeImport.objects.all().order_by('-upload_date')
    return render(request, 'leave/import_history.html', {'imports': imports})

@login_required
@user_passes_test(is_staff_or_manager)
def view_import_content(request, import_id):
    """Download processed CSV content from import record"""
    import_record = get_object_or_404(EmployeeImport, id=import_id)
    
    if import_record.csv_content:
        response = HttpResponse(import_record.csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="processed_{import_record.file_name}"'
        return response
    else:
        messages.error(request, "No CSV content available for this import.")
        return redirect('leave:import_history')

@login_required
def download_balances(request):
    """Download employee leave balances as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="employee_balances.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Employee ID', 'Name', 'Email', 'Department', 'Region',
        'Leave Type', 'Year', 'Opening Balance', 'Carried Forward',
        'Current Year Entitlement', 'Taken', 'Available Balance'
    ])
    
    # Get all employees with their leave balances
    employees = Employee.objects.select_related('user').prefetch_related('leave_balances').all()
    
    for employee in employees:
        balances = employee.leave_balances.all()
        if balances:
            for balance in balances:
                writer.writerow([
                    employee.employee_id,
                    employee.user.get_full_name(),
                    employee.user.email,
                    employee.department,
                    employee.get_region_display(),
                    balance.leave_type.name,
                    balance.year,
                    balance.opening_balance,
                    balance.carried_forward,
                    balance.current_year_entitlement,
                    balance.taken,
                    balance.balance
                ])
        else:
            # Employee with no leave balances
            writer.writerow([
                employee.employee_id,
                employee.user.get_full_name(),
                employee.user.email,
                employee.department,
                employee.get_region_display(),
                'No leave types assigned',
                '',
                '',
                '',
                '',
                '',
                ''
            ])
    
    return response

def process_employee_csv(csv_file, import_record, user):
    """Process the CSV file and import/update employees"""
    log_messages = []
    created_count = 0
    updated_count = 0
    error_count = 0
    
    try:
        # Read and decode the CSV file
        csv_file.seek(0)
        content = csv_file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content))
        
        # Track processed content for download
        processed_rows = []
        processed_rows.append(list(csv_reader.fieldnames) + ['Import Status', 'Notes'])
        
        total_rows = 0
        
        with transaction.atomic():
            for row_num, row in enumerate(csv_reader, start=2):
                total_rows += 1
                status = 'Success'
                notes = ''
                
                try:
                    # Extract required fields
                    username = row.get('username', '').strip()
                    email = row.get('email', '').strip()
                    first_name = row.get('first_name', '').strip()
                    last_name = row.get('last_name', '').strip()
                    
                    # Optional fields
                    date_joined = row.get('date_joined', '').strip()
                    region = row.get('region', 'HK').strip()
                    is_staff = row.get('is_staff', 'FALSE').strip().upper() == 'TRUE'
                    department = row.get('department', 'General').strip()
                    position = row.get('position', 'Staff').strip()
                    company = row.get('company', 'Krystal Institute Ltd').strip()
                    
                    # Leave balance fields
                    annual_leave = float(row.get('annual_leave_balance', 0) or 0)
                    sick_leave = float(row.get('sick_leave_balance', 0) or 0)
                    
                    # Validate required fields
                    if not all([username, email, first_name, last_name]):
                        raise ValueError("Missing required fields: username, email, first_name, last_name")
                    
                    # Parse date_joined
                    join_date = None
                    if date_joined:
                        try:
                            join_date = datetime.strptime(date_joined, '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                join_date = datetime.strptime(date_joined, '%m/%d/%Y').date()
                            except ValueError:
                                notes += "Invalid date format; "
                    
                    # Create or update user
                    user_obj, user_created = User.objects.get_or_create(
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
                        user_obj.email = email
                        user_obj.first_name = first_name
                        user_obj.last_name = last_name
                        user_obj.is_staff = is_staff
                        user_obj.save()
                        notes += "Updated user; "
                    else:
                        notes += "Created user; "
                    
                    # Create or update employee profile
                    employee, emp_created = Employee.objects.get_or_create(
                        user=user_obj,
                        defaults={
                            'employee_id': f"EMP{user_obj.id:04d}",
                            'department': department,
                            'position': position,
                            'company': company,
                            'date_joined': join_date,
                            'region': region
                        }
                    )
                    
                    if not emp_created:
                        # Update existing employee
                        employee.department = department
                        employee.position = position
                        employee.company = company
                        if join_date:
                            employee.date_joined = join_date
                        employee.region = region
                        employee.save()
                        updated_count += 1
                        notes += "Updated employee; "
                    else:
                        created_count += 1
                        notes += "Created employee; "
                    
                    # Handle leave balances
                    current_year = timezone.now().year
                    
                    # Annual Leave
                    if annual_leave > 0:
                        try:
                            annual_leave_type = LeaveType.objects.get(name='Annual Leave')
                            balance, bal_created = LeaveBalance.objects.get_or_create(
                                employee=employee,
                                leave_type=annual_leave_type,
                                year=current_year,
                                defaults={
                                    'opening_balance': Decimal('0.00'),
                                    'carried_forward': Decimal('0.00'),
                                    'current_year_entitlement': Decimal(str(annual_leave)),
                                    'taken': Decimal('0.00')
                                }
                            )
                            if not bal_created:
                                balance.current_year_entitlement = Decimal(str(annual_leave))
                                balance.save()
                            notes += f"Set Annual Leave: {annual_leave}; "
                        except LeaveType.DoesNotExist:
                            notes += "Annual Leave type not found; "
                    
                    # Sick Leave
                    if sick_leave > 0:
                        try:
                            sick_leave_type = LeaveType.objects.get(name='Sick Leave')
                            balance, bal_created = LeaveBalance.objects.get_or_create(
                                employee=employee,
                                leave_type=sick_leave_type,
                                year=current_year,
                                defaults={
                                    'opening_balance': Decimal('0.00'),
                                    'carried_forward': Decimal('0.00'),
                                    'current_year_entitlement': Decimal(str(sick_leave)),
                                    'taken': Decimal('0.00')
                                }
                            )
                            if not bal_created:
                                balance.current_year_entitlement = Decimal(str(sick_leave))
                                balance.save()
                            notes += f"Set Sick Leave: {sick_leave}; "
                        except LeaveType.DoesNotExist:
                            notes += "Sick Leave type not found; "
                    
                    log_messages.append(f"Row {row_num}: Successfully processed {username}")
                    
                except Exception as e:
                    error_count += 1
                    status = 'Error'
                    notes = str(e)
                    log_messages.append(f"Row {row_num}: Error - {str(e)}")
                
                # Add to processed rows
                processed_row = list(row.values()) + [status, notes]
                processed_rows.append(processed_row)
        
        # Determine overall status
        if error_count == 0:
            status = 'success'
        elif error_count < total_rows:
            status = 'partial'
        else:
            status = 'failed'
        
        # Create CSV content for download
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerows(processed_rows)
        csv_content = output.getvalue()
        
        return {
            'status': status,
            'total_rows': total_rows,
            'created_count': created_count,
            'updated_count': updated_count,
            'error_count': error_count,
            'log': '\n'.join(log_messages),
            'csv_content': csv_content
        }
        
    except Exception as e:
        log_messages.append(f"Fatal error: {str(e)}")
        return {
            'status': 'failed',
            'total_rows': 0,
            'created_count': 0,
            'updated_count': 0,
            'error_count': 1,
            'log': '\n'.join(log_messages),
            'csv_content': ''
        }

@login_required
def special_work_claim(request):
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return render(request, "leave/no_profile.html")
    
    # Get or create special leave balance for the employee
    balance_info, created = SpecialLeaveBalance.objects.get_or_create(
        employee=employee,
        defaults={'earned': 0.0, 'used': 0.0}
    )
    
    if request.method == 'POST':
        form = SpecialWorkClaimForm(request.POST)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.employee = employee
            claim.save()
            
            messages.success(request, 'Special work claim submitted successfully! Awaiting manager approval.')
            return redirect('leave:special_work_claim')
    else:
        form = SpecialWorkClaimForm()
    
    # Get user's claims with pagination
    from django.core.paginator import Paginator
    claims_list = SpecialWorkClaim.objects.filter(employee=employee).order_by('-created_at')
    paginator = Paginator(claims_list, 10)
    page_number = request.GET.get('page')
    claims = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'employee': employee,
        'balance_info': balance_info,
        'claims': claims,
    }
    
    return render(request, 'leave/special_work_claim.html', context)

@login_required
def special_leave_apply(request):
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return render(request, "leave/no_profile.html")
    
    # Get or create special leave balance for the employee
    balance_info, created = SpecialLeaveBalance.objects.get_or_create(
        employee=employee,
        defaults={'earned': 0.0, 'used': 0.0}
    )
    
    if request.method == 'POST':
        form = SpecialLeaveApplicationForm(request.POST, employee=employee)
        if form.is_valid():
            application = form.save(commit=False)
            application.employee = employee
            application.save()
            
            messages.success(request, 'Special leave application submitted successfully!')
            return redirect('leave:special_leave_apply_confirm', application_id=application.id)
    else:
        form = SpecialLeaveApplicationForm(employee=employee)
    
    # Get user's special leave applications
    applications = SpecialLeaveApplication.objects.filter(employee=employee).order_by('-created_at')[:5]
    
    context = {
        'form': form,
        'employee': employee,
        'balance_info': balance_info,
        'applications': applications,
        'is_revision': False
    }
    
    return render(request, 'leave/special_leave_apply.html', context)

@login_required
def special_leave_apply_confirm(request, application_id):
    application = get_object_or_404(SpecialLeaveApplication, pk=application_id, employee__user=request.user)
    
    if request.method == 'POST':
        if 'confirm' in request.POST:
            # Application is already saved, just redirect to applications list
            messages.success(request, 'Special leave application confirmed!')
            return redirect('leave:special_leave_management')
        elif 'edit' in request.POST:
            # Redirect back to apply form
            return redirect('leave:special_leave_apply')
    
    # Calculate back to office date
    date_back = calculate_return_date(application.date_to)
    
    # Prepare context data for template
    context = {
        'employee': application.employee,
        'application_data': {
            'days_applied': application.days_applied,
            'reason': application.reason,
            'credits_used': application.credits_used,
        },
        'start_date_display': application.date_from.strftime('%A, %B %d, %Y'),
        'start_time_display': 'AM (9:00am - 1:00pm)' if application.date_from.hour == 9 else 'PM (2:00pm - 6:00pm)',
        'end_date_display': application.date_to.strftime('%A, %B %d, %Y'),
        'end_time_display': 'AM (9:00am - 1:00pm)' if application.date_to.hour == 13 else 'PM (2:00pm - 6:00pm)',
        'date_back_to_work': date_back,
        'is_revision': False
    }
    
    return render(request, 'leave/special_leave_apply_confirm.html', context)

@login_required
def special_leave_management(request):
    return render(request, 'leave/special_leave_management.html', {'message': 'Feature coming soon'})

@login_required
def holiday_edit(request, holiday_id):
    return render(request, 'leave/holiday_edit.html', {'message': 'Feature coming soon'})

@login_required
def holiday_delete(request, holiday_id):
    return render(request, 'leave/holiday_delete.html', {'message': 'Feature coming soon'})

@login_required
def combined_print(request):
    """Combined print view for printing 2 applications on one A4 page"""
    ids_param = request.GET.get('ids', '')
    
    if not ids_param:
        messages.error(request, 'No applications selected for combined printing.')
        return redirect('leave:leave_applications')
    
    # Parse application IDs
    try:
        app_ids = [int(id_str.strip()) for id_str in ids_param.split(',') if id_str.strip()]
    except ValueError:
        messages.error(request, 'Invalid application IDs provided.')
        return redirect('leave:leave_applications')
    
    if not app_ids:
        messages.error(request, 'No valid application IDs provided.')
        return redirect('leave:leave_applications')
    
    # Get applications (limit to 2 for combined printing)
    applications = []
    dates_back_to_work = []
    
    for app_id in app_ids[:2]:  # Only take first 2 applications
        try:
            app = LeaveApplication.objects.get(pk=app_id)
            # Check if user has permission to view this application
            if not request.user.is_staff and app.employee.user != request.user:
                messages.error(request, f'You do not have permission to view application {app_id}.')
                return redirect('leave:leave_applications')
            
            applications.append(app)
            dates_back_to_work.append(calculate_return_date(app.date_to))
        except LeaveApplication.DoesNotExist:
            messages.warning(request, f'Application {app_id} not found.')
    
    if not applications:
        messages.error(request, 'No valid applications found for printing.')
        return redirect('leave:leave_applications')
    
    # Pad with None if less than 2 applications
    while len(applications) < 2:
        applications.append(None)
        dates_back_to_work.append(None)
    
    context = {
        'applications': applications,
        'dates_back_to_work': dates_back_to_work,
        'application_ids_param': ids_param,
        'is_pdf': False,
    }
    
    return render(request, 'leave/combined_print.html', context)

@login_required
def combined_print_pdf(request):
    """Generate PDF for combined applications"""
    ids_param = request.GET.get('ids', '')
    
    if not ids_param:
        messages.error(request, 'No applications selected for PDF generation.')
        return redirect('leave:leave_applications')
    
    # Parse application IDs
    try:
        app_ids = [int(id_str.strip()) for id_str in ids_param.split(',') if id_str.strip()]
    except ValueError:
        messages.error(request, 'Invalid application IDs provided.')
        return redirect('leave:leave_applications')
    
    if not app_ids:
        messages.error(request, 'No valid application IDs provided.')
        return redirect('leave:leave_applications')
    
    # Get applications (limit to 2 for combined printing)
    applications = []
    dates_back_to_work = []
    
    for app_id in app_ids[:2]:  # Only take first 2 applications
        try:
            app = LeaveApplication.objects.get(pk=app_id)
            # Check if user has permission to view this application
            if not request.user.is_staff and app.employee.user != request.user:
                messages.error(request, f'You do not have permission to view application {app_id}.')
                return redirect('leave:leave_applications')
            
            applications.append(app)
            dates_back_to_work.append(calculate_return_date(app.date_to))
        except LeaveApplication.DoesNotExist:
            messages.warning(request, f'Application {app_id} not found.')
    
    if not applications:
        messages.error(request, 'No valid applications found for PDF generation.')
        return redirect('leave:leave_applications')
    
    # Pad with None if less than 2 applications
    while len(applications) < 2:
        applications.append(None)
        dates_back_to_work.append(None)
    
    template = get_template('leave/combined_print.html')
    context = {
        'applications': applications,
        'dates_back_to_work': dates_back_to_work,
        'application_ids_param': ids_param,
        'is_pdf': True,
    }
    html = template.render(context)
    
    try:
        # Try to generate PDF using weasyprint if available
        import weasyprint
        pdf_file = weasyprint.HTML(string=html).write_pdf()
        
        # Create filename with employee names
        employee_names = []
        for app in applications:
            if app:
                name = app.employee.user.get_full_name().replace(" ", "_")
                employee_names.append(name)
        
        filename = f'combined_leave_applications_{"_".join(employee_names)}.pdf'
        
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    except ImportError:
        # If weasyprint is not available, redirect to print view with warning
        messages.warning(request, 'PDF generation is not available. Please use the print function instead.')
        return redirect(f"{reverse('leave:combined_print')}?ids={ids_param}")

# Manager Approval Views
@user_passes_test(is_manager)
def manager_dashboard(request):
    """Manager dashboard showing pending approvals"""
    # Get pending leave applications
    pending_leaves = LeaveApplication.objects.filter(status='pending').order_by('-created_at')
    
    # Get pending special work claims
    pending_claims = SpecialWorkClaim.objects.filter(status='pending').order_by('-created_at')
    
    # Get pending special leave applications
    pending_special_leaves = SpecialLeaveApplication.objects.filter(status='pending').order_by('-created_at')
    
    context = {
        'pending_leaves': pending_leaves,
        'pending_claims': pending_claims,
        'pending_special_leaves': pending_special_leaves,
    }
    
    return render(request, 'leave/manager_dashboard.html', context)

@user_passes_test(is_manager)
def approve_leave_application(request, application_id):
    """Approve or reject leave application"""
    application = get_object_or_404(LeaveApplication, pk=application_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        
        if action == 'approve':
            application.status = 'approved'
            application.approved_by = request.user
            application.approved_at = timezone.now()
            messages.success(request, f'Leave application for {application.employee.user.get_full_name()} approved successfully.')
        elif action == 'reject':
            application.status = 'rejected'
            application.approved_by = request.user
            application.approved_at = timezone.now()
            messages.success(request, f'Leave application for {application.employee.user.get_full_name()} rejected.')
        
        application.save()
        return redirect('leave:manager_dashboard')
    
    context = {
        'application': application,
        'date_back_to_work': calculate_return_date(application.date_to),
    }
    
    return render(request, 'leave/approve_leave_application.html', context)

@user_passes_test(is_manager)
def approve_special_work_claim(request, claim_id):
    """Approve or reject special work claim"""
    claim = get_object_or_404(SpecialWorkClaim, pk=claim_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        
        if action == 'approve':
            claim.status = 'approved'
            claim.approved_by = request.user
            claim.approved_at = timezone.now()
            claim.manager_comment = comment
            
            # Add credits to employee's balance
            balance, created = SpecialLeaveBalance.objects.get_or_create(
                employee=claim.employee,
                defaults={'earned': 0.0, 'used': 0.0}
            )
            balance.earned += claim.credits_earned
            balance.save()
            
            messages.success(request, f'Special work claim for {claim.employee.user.get_full_name()} approved successfully. {claim.credits_earned} credits added.')
            
        elif action == 'reject':
            claim.status = 'rejected'
            claim.approved_by = request.user
            claim.approved_at = timezone.now()
            claim.manager_comment = comment
            messages.success(request, f'Special work claim for {claim.employee.user.get_full_name()} rejected.')
        
        claim.save()
        return redirect('leave:manager_dashboard')
    
    context = {
        'claim': claim,
    }
    
    return render(request, 'leave/approve_special_work_claim.html', context)

@user_passes_test(is_manager)
def approve_special_leave_application(request, application_id):
    """Approve or reject special leave application"""
    application = get_object_or_404(SpecialLeaveApplication, pk=application_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        
        if action == 'approve':
            application.status = 'approved'
            application.approved_by = request.user
            application.approved_at = timezone.now()
            
            # Deduct credits from employee's balance
            try:
                balance = SpecialLeaveBalance.objects.get(employee=application.employee)
                balance.used += application.credits_used
                balance.save()
                messages.success(request, f'Special leave application for {application.employee.user.get_full_name()} approved successfully. {application.credits_used} credits deducted.')
            except SpecialLeaveBalance.DoesNotExist:
                messages.error(request, 'Error: Employee special leave balance not found.')
                return redirect('leave:manager_dashboard')
            
        elif action == 'reject':
            application.status = 'rejected'
            application.approved_by = request.user
            application.approved_at = timezone.now()
            messages.success(request, f'Special leave application for {application.employee.user.get_full_name()} rejected.')
        
        application.save()
        return redirect('leave:manager_dashboard')
    
    context = {
        'application': application,
        'date_back_to_work': calculate_return_date(application.date_to),
    }
    
    return render(request, 'leave/approve_special_leave_application.html', context)
