from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from .models import EmployeeProfile, LeaveApplication, LeaveBalance, LeaveType
from datetime import date
from decimal import Decimal

class CustomLoginView(LoginView):
    template_name = "leave/login.html"

    def get_success_url(self):
        return reverse_lazy("leave:dashboard")

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("leave:login")

@login_required
def dashboard(request):
    # Initialize variables that will always be needed
    current_year = date.today().year
    
    try:
        employee = EmployeeProfile.objects.get(user=request.user)
        
        # Get recent applications
        applications = LeaveApplication.objects.filter(employee=employee).order_by('-created_at')
        
        # Get or create leave balances for current year
        leave_balances = {}
        
        # Get all leave types
        leave_types = LeaveType.objects.all()
        
        for leave_type in leave_types:
            balance, created = LeaveBalance.objects.get_or_create(
                employee=employee,
                leave_type=leave_type,
                year=current_year,
                defaults={
                    'opening_balance': Decimal('0.00'),
                    'carried_forward': Decimal('0.00'),
                    'current_year_entitlement': employee.get_annual_leave_entitlement() if leave_type.name == 'Annual Leave' else Decimal('0.00'),
                }
            )
            # Recalculate balance
            balance.calculate_balance()
            balance.save()
            leave_balances[leave_type.name] = balance
        
        # Calculate additional statistics
        stats = {
            'years_of_service': employee.years_of_service(),
            'total_applications_this_year': applications.filter(date_from__year=current_year).count(),
            'pending_applications': applications.filter(status='pending').count(),
        }
        
        # Add special leave statistics for managers
        if request.user.is_staff:
            from .models import SpecialWorkClaim, SpecialLeaveApplication
            pending_claims = SpecialWorkClaim.objects.filter(status='pending').count()
            pending_special_applications = SpecialLeaveApplication.objects.filter(status='pending').count()
            stats.update({
                'pending_special_claims': pending_claims,
                'pending_special_applications': pending_special_applications,
                'total_pending_special': pending_claims + pending_special_applications,
            })
        
        # Get detailed annual leave balance
        annual_leave_details = employee.get_detailed_annual_leave_balance(current_year)
        
        # Get special leave balance
        special_leave_balance = employee.get_special_leave_balance()
        
    except EmployeeProfile.DoesNotExist:
        applications = None
        employee = None
        leave_balances = {}
        stats = {}
        annual_leave_details = {}
        special_leave_balance = {'earned': 0, 'used': 0, 'balance': 0}
    
    return render(request, "leave/dashboard.html", {
        "applications": applications,
        "employee": employee,
        "leave_balances": leave_balances,
        "stats": stats,
        "current_year": current_year,
        "annual_leave_details": annual_leave_details,
        "special_leave_balance": special_leave_balance,
    })


def register(request):
    """User registration view"""
    from django.contrib.auth.models import User
    from django.contrib.auth import login
    from django.contrib import messages
    from .forms import UserRegistrationForm
    from .models import EmployeeProfile, LeaveType, LeaveBalance
    from datetime import datetime
    from decimal import Decimal
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Generate username from email
                email = form.cleaned_data['email']
                username = form.generate_username_from_email(email)
                
                # Create user with email as primary identifier
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=form.cleaned_data['password1'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name']
                )
                
                # Create employee profile
                employee_profile = EmployeeProfile.objects.create(
                    user=user,
                    date_joined=form.cleaned_data['date_joined'],
                    region=form.cleaned_data['region']
                )
                
                # Create initial leave balances
                current_year = datetime.now().year
                leave_types = LeaveType.objects.all()
                
                for leave_type in leave_types:
                    if leave_type.name == 'Annual Leave':
                        entitlement = employee_profile.get_annual_leave_entitlement()
                    else:
                        entitlement = Decimal('0.00')
                    
                    LeaveBalance.objects.create(
                        employee=employee_profile,
                        leave_type=leave_type,
                        year=current_year,
                        opening_balance=Decimal('0.00'),
                        carried_forward=Decimal('0.00'),
                        current_year_entitlement=entitlement,
                        balance=entitlement,
                        taken=Decimal('0.00')
                    )
                
                # Log the user in
                login(request, user)
                messages.success(request, f'Welcome {user.first_name}! Your account has been created successfully.')
                return redirect('leave:dashboard')
                
            except Exception as e:
                messages.error(request, f'Error creating account: {str(e)}')
        else:
            # Form has validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field.title()}: {error}')
    
    return redirect('leave:login')