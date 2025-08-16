from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Employee, LeaveApplication, LeaveType, PendingRegistration
from .forms import StaffRegistrationForm
from datetime import date
from decimal import Decimal

class CustomLoginView(LoginView):
    template_name = "leave/login.html"
    
    def get_success_url(self):
        return reverse_lazy("leave:dashboard")

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("leave:login")

def register(request):
    if request.method == "POST":
        form = StaffRegistrationForm(request.POST)
        if form.is_valid():
            # Create pending registration
            PendingRegistration.objects.create(
                email=form.cleaned_data['email'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                other_name=form.cleaned_data['other_name'],
                office_location=form.cleaned_data['office_location']
            )
            messages.success(
                request, 
                'Registration submitted successfully! Please wait for admin approval. '
                'You will be contacted via email once your registration is reviewed.'
            )
            return redirect('leave:register')
    else:
        form = StaffRegistrationForm()
    
    return render(request, "leave/register.html", {'form': form})

@login_required
def dashboard(request):
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return render(request, "leave/no_profile.html")
    
    # Get recent leave applications
    recent_applications = LeaveApplication.objects.filter(
        employee=employee
    ).order_by('-created_at')[:5]
    
    # Get all leave types
    leave_types = LeaveType.objects.all()
    
    context = {
        'employee': employee,
        'recent_applications': recent_applications,
        'leave_types': leave_types,
    }
    
    return render(request, "leave/dashboard.html", context)
