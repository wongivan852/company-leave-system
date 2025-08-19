from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User
from .models import LeaveApplication, LeaveType, SpecialWorkClaim, SpecialLeaveApplication
from datetime import datetime, time

class LeaveApplicationForm(forms.ModelForm):
    SESSION_CHOICES = [
        ('AM', 'AM (9:00am - 1:00pm)'),
        ('PM', 'PM (2:00pm - 6:00pm)'),
    ]
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    start_session = forms.ChoiceField(
        choices=SESSION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_session = forms.ChoiceField(
        choices=SESSION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        self.employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        
        # Add custom styling
        for field_name, field in self.fields.items():
            if field_name in ['leave_type', 'reason']:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Set the queryset for leave types
        if self.employee:
            self.fields['leave_type'].queryset = LeaveType.objects.all()
        
        # If editing existing application, populate session fields
        if self.instance.pk:
            if hasattr(self.instance, 'date_from') and self.instance.date_from:
                self.fields['start_date'].initial = self.instance.date_from.date()
                self.fields['start_session'].initial = 'AM' if self.instance.date_from.hour == 9 else 'PM'
            if hasattr(self.instance, 'date_to') and self.instance.date_to:
                self.fields['end_date'].initial = self.instance.date_to.date()
                self.fields['end_session'].initial = 'AM' if self.instance.date_to.hour == 13 else 'PM'
    
    class Meta:
        model = LeaveApplication
        fields = ['leave_type', 'reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        start_session = cleaned_data.get('start_session')
        end_date = cleaned_data.get('end_date')
        end_session = cleaned_data.get('end_session')
        
        if start_date and end_date:
            # Validate date order
            if end_date < start_date:
                raise ValidationError("End date cannot be before start date.")
            
            # Validate that start date is not in the past
            from django.utils import timezone
            if start_date < timezone.now().date():
                raise ValidationError("Leave cannot start in the past.")
            
            # Validate weekend restrictions
            if start_date.weekday() >= 5 or end_date.weekday() >= 5:
                raise ValidationError("Leave cannot start or end on weekends.")
        
        return cleaned_data
    
    def save(self, commit=True):
        application = super().save(commit=False)
        
        # Set the employee
        if self.employee:
            application.employee = self.employee
        
        # Convert session selections to datetime
        from datetime import datetime, time
        
        start_date = self.cleaned_data['start_date']
        start_session = self.cleaned_data['start_session']
        end_date = self.cleaned_data['end_date']
        end_session = self.cleaned_data['end_session']
        
        # Set start datetime
        if start_session == 'AM':
            application.date_from = datetime.combine(start_date, time(9, 0))
        else:  # PM
            application.date_from = datetime.combine(start_date, time(14, 0))
        
        # Set end datetime
        if end_session == 'AM':
            application.date_to = datetime.combine(end_date, time(13, 0))
        else:  # PM
            application.date_to = datetime.combine(end_date, time(18, 0))
        
        if commit:
            application.save()
        return application


class StaffRegistrationForm(forms.Form):
    LOCATION_CHOICES = [
        ('HK', 'Hong Kong'),
        ('CN', 'China'),
        ('OTHER', 'Other'),
    ]
    
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'})
    )
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your first name'})
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your last name'})
    )
    other_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter other name (optional)'})
    )
    office_location = forms.ChoiceField(
        choices=LOCATION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email


class SpecialWorkClaimForm(forms.ModelForm):
    SESSION_CHOICES = [
        ('AM', 'AM (9:00am - 1:00pm)'),
        ('PM', 'PM (2:00pm - 6:00pm)'),
        ('FULL', 'Full Day (9:00am - 6:00pm)'),
    ]
    
    work_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Work Date'
    )
    work_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='End Date',
        help_text='Leave blank for single day'
    )
    session = forms.ChoiceField(
        choices=SESSION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Session'
    )
    
    class Meta:
        model = SpecialWorkClaim
        fields = ['work_date', 'work_end_date', 'session', 'event_name', 'description', 'priority']
        widgets = {
            'event_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Easter Sunday Event, Christmas Setup'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe the work performed...'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        work_date = cleaned_data.get('work_date')
        work_end_date = cleaned_data.get('work_end_date')
        
        if work_date:
            # Validate that work date is not in the future (more than 30 days)
            from datetime import timedelta
            max_date = timezone.now().date() + timedelta(days=30)
            if work_date > max_date:
                raise ValidationError("Work date cannot be more than 30 days in the future.")
        
        if work_end_date:
            if work_date and work_end_date < work_date:
                raise ValidationError("End date cannot be before start date.")
            
            if work_date and work_end_date:
                days_diff = (work_end_date - work_date).days + 1
                if days_diff > 14:
                    raise ValidationError("Maximum 14 consecutive days allowed per claim.")
        
        return cleaned_data


class SpecialLeaveApplicationForm(forms.ModelForm):
    SESSION_CHOICES = [
        ('AM', 'AM (9:00am - 1:00pm)'),
        ('PM', 'PM (2:00pm - 6:00pm)'),
    ]
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    start_session = forms.ChoiceField(
        choices=SESSION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_session = forms.ChoiceField(
        choices=SESSION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        self.employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        
        # Add custom styling
        for field_name, field in self.fields.items():
            if field_name == 'reason':
                field.widget.attrs.update({'class': 'form-control'})
        
        # If editing existing application, populate session fields
        if self.instance.pk:
            if hasattr(self.instance, 'date_from') and self.instance.date_from:
                self.fields['start_date'].initial = self.instance.date_from.date()
                self.fields['start_session'].initial = 'AM' if self.instance.date_from.hour == 9 else 'PM'
            if hasattr(self.instance, 'date_to') and self.instance.date_to:
                self.fields['end_date'].initial = self.instance.date_to.date()
                self.fields['end_session'].initial = 'AM' if self.instance.date_to.hour == 13 else 'PM'
    
    class Meta:
        model = SpecialLeaveApplication
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        start_session = cleaned_data.get('start_session')
        end_date = cleaned_data.get('end_date')
        end_session = cleaned_data.get('end_session')
        
        if start_date and end_date:
            # Validate date order
            if end_date < start_date:
                raise ValidationError("End date cannot be before start date.")
            
            # Validate that start date is not in the past
            if start_date < timezone.now().date():
                raise ValidationError("Leave cannot start in the past.")
            
            # Validate weekend restrictions
            if start_date.weekday() >= 5 or end_date.weekday() >= 5:
                raise ValidationError("Leave cannot start or end on weekends.")
        
        # Check if employee has enough special leave credits
        if self.employee:
            from .models import SpecialLeaveBalance
            try:
                balance = SpecialLeaveBalance.objects.get(employee=self.employee)
                # Calculate required credits
                temp_app = SpecialLeaveApplication()
                if start_date and start_session:
                    temp_app.date_from = datetime.combine(start_date, time(9, 0) if start_session == 'AM' else time(14, 0))
                if end_date and end_session:
                    temp_app.date_to = datetime.combine(end_date, time(13, 0) if end_session == 'AM' else time(18, 0))
                
                required_credits = temp_app.calculate_days()
                if required_credits > balance.balance:
                    raise ValidationError(f"Insufficient special leave credits. Required: {required_credits}, Available: {balance.balance}")
            except SpecialLeaveBalance.DoesNotExist:
                raise ValidationError("No special leave balance found. Please contact HR.")
        
        return cleaned_data
    
    def save(self, commit=True):
        application = super().save(commit=False)
        
        # Set the employee
        if self.employee:
            application.employee = self.employee
        
        # Convert session selections to datetime
        start_date = self.cleaned_data['start_date']
        start_session = self.cleaned_data['start_session']
        end_date = self.cleaned_data['end_date']
        end_session = self.cleaned_data['end_session']
        
        # Set start datetime
        if start_session == 'AM':
            application.date_from = datetime.combine(start_date, time(9, 0))
        else:  # PM
            application.date_from = datetime.combine(start_date, time(14, 0))
        
        # Set end datetime
        if end_session == 'AM':
            application.date_to = datetime.combine(end_date, time(13, 0))
        else:  # PM
            application.date_to = datetime.combine(end_date, time(18, 0))
        
        if commit:
            application.save()
        return application


# NEW FORM FOR EMPLOYEE IMPORT
class EmployeeImportForm(forms.Form):
    csv_file = forms.FileField(
        label='CSV File',
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'accept': '.csv',
            'help_text': 'Upload a CSV file with employee data'
        })
    )
    
    def clean_csv_file(self):
        file = self.cleaned_data.get('csv_file')
        
        if file:
            # Check file size (limit to 5MB)
            if file.size > 5 * 1024 * 1024:
                raise ValidationError("File size cannot exceed 5MB.")
            
            # Check file extension
            if not file.name.lower().endswith('.csv'):
                raise ValidationError("Only CSV files are allowed.")
            
            # Try to read and validate CSV structure
            try:
                file.seek(0)  # Reset file pointer
                content = file.read().decode('utf-8')
                file.seek(0)  # Reset again for later use
                
                lines = content.split('\n')
                if len(lines) < 2:
                    raise ValidationError("CSV file must contain at least a header and one data row.")
                
                # Check for required columns
                header = lines[0].lower()
                required_fields = ['username', 'email', 'first_name', 'last_name']
                missing_fields = [field for field in required_fields if field not in header]
                
                if missing_fields:
                    raise ValidationError(f"Missing required columns: {', '.join(missing_fields)}")
                    
            except UnicodeDecodeError:
                raise ValidationError("File must be in UTF-8 format.")
            except Exception as e:
                raise ValidationError(f"Error reading CSV file: {str(e)}")
        
        return file