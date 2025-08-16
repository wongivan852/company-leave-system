from datetime import datetime, timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import get_template
# weasyprint will be imported dynamically when needed
from .models import LeaveApplication, LeaveType, Employee, SpecialWorkClaim, SpecialLeaveApplication, SpecialLeaveBalance
from .forms import LeaveApplicationForm, SpecialWorkClaimForm, SpecialLeaveApplicationForm
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User

def is_manager(user):
    """Check if user is admin or magneoh (managers)"""
    return user.is_authenticated and (user.username in ['admin', 'magneoh'] or user.is_superuser)

def calculate_return_date(date_to):
    """Calculate the return to work date based on the leave end date."""
    # If leave ends in the morning (before 1 PM), return same day afternoon
    if date_to.hour < 13:
        return date_to.date()
    
    # If leave ends in the afternoon, return next working day morning
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
def employee_import(request):
    return render(request, 'leave/employee_import.html', {'message': 'Feature coming soon'})

@login_required
def import_history(request):
    return render(request, 'leave/import_history.html', {'message': 'Feature coming soon'})

@login_required
def view_import_content(request, import_id):
    return render(request, 'leave/view_import.html', {'message': 'Feature coming soon'})

@login_required
def download_balances(request):
    return HttpResponse('Feature coming soon')

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
    return render(request, 'leave/combined_print.html', {'message': 'Feature coming soon'})

@login_required
def combined_print_pdf(request):
    return HttpResponse('Feature coming soon - PDF generation')

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
