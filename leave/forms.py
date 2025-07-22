from django import forms
from .models import LeaveApplication, LeaveType, SpecialWorkClaim, SpecialLeaveApplication
from datetime import datetime, date, time, timedelta
from decimal import Decimal

class LeaveApplicationForm(forms.ModelForm):
    TIME_CHOICES = [
        ('AM', 'AM (9:00)'),
        ('PM', 'PM (13:00)'),
    ]
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px;'
        })
    )
    start_time = forms.ChoiceField(
        choices=TIME_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px;'
        })
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px;'
        })
    )
    end_time = forms.ChoiceField(
        choices=TIME_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px;'
        })
    )

    class Meta:
        model = LeaveApplication
        fields = ['leave_type', 'reason', 'certificate']

        widgets = {
            'reason': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px;',
                'placeholder': 'Please provide reason for your leave request...'
            }),
            'leave_type': forms.Select(attrs={
                'class': 'form-control',
                'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px;'
            }),
            'certificate': forms.FileInput(attrs={
                'class': 'form-control',
                'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px;',
                'accept': '.jpg,.jpeg,.png,.pdf'
            })
        }

    def __init__(self, *args, **kwargs):
        self.employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        self.fields['certificate'].required = False
        self.fields['leave_type'].empty_label = "Select Leave Type"
        self.fields['reason'].required = False
        
        # Set default values for date and time fields
        if not self.instance.pk:  # Only for new applications
            today = date.today()
            self.fields['start_date'].initial = today
            self.fields['end_date'].initial = today
            self.fields['start_time'].initial = 'AM'
            self.fields['end_time'].initial = 'PM'
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        start_time = cleaned_data.get('start_time')
        end_date = cleaned_data.get('end_date')
        end_time = cleaned_data.get('end_time')
        leave_type = cleaned_data.get('leave_type')
        
        if start_date and start_time and end_date and end_time:
            # Convert AM/PM to actual time objects
            start_time_obj = time(9, 0) if start_time == 'AM' else time(13, 0)  # 9:00 AM or 1:00 PM
            end_time_obj = time(13, 0) if end_time == 'AM' else time(18, 0)    # 1:00 PM or 6:00 PM
            
            # Create datetime objects
            date_from = datetime.combine(start_date, start_time_obj)
            date_to = datetime.combine(end_date, end_time_obj)
            
            # Store the combined datetime values for model saving
            cleaned_data['date_from'] = date_from
            cleaned_data['date_to'] = date_to
            # Store the combined datetime values for model saving
            cleaned_data['date_from'] = date_from
            cleaned_data['date_to'] = date_to
        
        if cleaned_data.get('date_from') and cleaned_data.get('date_to'):
            date_from = cleaned_data['date_from']
            date_to = cleaned_data['date_to']
            
            # Check if end date is after start date
            if date_to <= date_from:
                raise forms.ValidationError("End date and time must be after start date and time.")
            
            # Check if dates are not in the past (except for today)
            now = datetime.now()
            if date_from.date() < date.today():
                raise forms.ValidationError("Leave start date cannot be in the past.")
            
            # Create a temporary leave application to calculate days
            temp_application = LeaveApplication(
                employee=self.employee,
                date_from=date_from,
                date_to=date_to,
                leave_type=leave_type
            )
            
            # Calculate days using the new calendar logic
            try:
                days_applied = temp_application.calculate_leave_days()
                
                # Check if the result is 0 (likely weekend/holiday selection)
                if days_applied == 0:
                    # Check if it's because of weekend selection
                    start_weekday = date_from.weekday()  # Monday=0, Sunday=6
                    end_weekday = date_to.weekday()
                    
                    if start_weekday >= 5 or end_weekday >= 5:  # Saturday=5, Sunday=6
                        raise forms.ValidationError(
                            "Selected dates include weekend(s). Leave applications should be for business days only. "
                            "Please select weekdays (Monday to Friday)."
                        )
                    else:
                        raise forms.ValidationError(
                            "Selected dates include holidays only. Please select working days for your leave application."
                        )
                
                # Check minimum 0.5 day requirement
                if days_applied < 0.5:
                    raise forms.ValidationError("Minimum leave application is 0.5 day (half day).")
                
                # Check maximum reasonable duration (e.g., 365 days)
                if days_applied > 365:
                    raise forms.ValidationError("Leave duration cannot exceed 365 days.")
                
                cleaned_data['days_applied'] = days_applied
                
                # Add helpful message for half-day applications
                if days_applied == 0.5:
                    cleaned_data['half_day_notice'] = "This is a half-day leave application."
                elif days_applied == 1.0 and not temp_application.includes_saturday_work:
                    cleaned_data['full_day_notice'] = "This is a full-day leave application."
                
                # Get holiday information for display
                holidays_in_period = temp_application.get_holiday_info()
                cleaned_data['holidays_in_period'] = holidays_in_period
                
                # Saturday working day information and warning
                cleaned_data['includes_saturday_work'] = temp_application.includes_saturday_work
                cleaned_data['saturday_work_days'] = temp_application.saturday_work_days
                
                # Add Saturday working day warning message
                if temp_application.includes_saturday_work and temp_application.saturday_work_days > 0:
                    saturday_warning = f"⚠️ NOTICE: Your leave application includes {int(temp_application.saturday_work_days)} Friday(s). " \
                                     f"According to company policy, Saturday(s) is viewed as working day(s) thus respective Saturday would be counted as annual leave application. " \
                                     f"Total leave deduction: {days_applied} days " \
                                     f"({days_applied - temp_application.saturday_work_days} business days + {int(temp_application.saturday_work_days)} Saturday working days)."
                    
                    # Store the warning message for display
                    cleaned_data['saturday_warning'] = saturday_warning
                
            except forms.ValidationError as ve:
                # Re-raise ValidationError as-is to preserve proper error formatting
                raise ve
            except Exception as e:
                raise forms.ValidationError(f"Error calculating leave days: {str(e)}")
        
        # Validate sick leave certificate requirement
        if leave_type and leave_type.name == 'Sick Leave':
            certificate = cleaned_data.get('certificate')
            # If it's more than 3 days and no certificate, warn but don't block
            if 'days_applied' in cleaned_data and cleaned_data['days_applied'] > 3 and not certificate:
                # Add a warning message but don't prevent submission
                pass
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set the date_from and date_to from cleaned_data
        if hasattr(self, 'cleaned_data'):
            if 'date_from' in self.cleaned_data:
                instance.date_from = self.cleaned_data['date_from']
            if 'date_to' in self.cleaned_data:
                instance.date_to = self.cleaned_data['date_to']
            if 'days_applied' in self.cleaned_data:
                instance.days_applied = self.cleaned_data['days_applied']
            if 'includes_saturday_work' in self.cleaned_data:
                instance.includes_saturday_work = self.cleaned_data['includes_saturday_work']
            if 'saturday_work_days' in self.cleaned_data:
                instance.saturday_work_days = self.cleaned_data['saturday_work_days']
        
        if commit:
            instance.save()
        return instance


class UserRegistrationForm(forms.Form):
    """Form for user registration"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address',
            'required': True
        }),
        help_text='This will be your login email and must be unique.'
    )
    
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name',
            'required': True
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name',
            'required': True
        })
    )
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'required': True
        }),
        help_text='Your password must be at least 8 characters long.'
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password',
            'required': True
        }),
        help_text='Enter the same password as before, for verification.'
    )
    
    date_joined = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'required': True
        }),
        help_text='Your employment start date'
    )
    
    region = forms.ChoiceField(
        choices=[('HK', 'Hong Kong'), ('CN', 'China')],
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True
        }),
        initial='HK'
    )
    
    def clean_email(self):
        from django.contrib.auth.models import User
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address is already registered.')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError('The two password fields must match.')
            if len(password1) < 8:
                raise forms.ValidationError('Password must be at least 8 characters long.')
        
        return cleaned_data
    
    def generate_username_from_email(self, email):
        """Generate a unique username from email"""
        from django.contrib.auth.models import User
        import re
        
        # Extract base username from email (part before @)
        base_username = email.split('@')[0]
        
        # Clean username - only letters, numbers, underscores
        base_username = re.sub(r'[^a-zA-Z0-9_]', '_', base_username)
        
        # Ensure it's not too long
        base_username = base_username[:30]
        
        # Check if username exists, if so, add number suffix
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
            # Ensure total length doesn't exceed 150 chars
            if len(username) > 150:
                username = f"user_{counter}"
        
        return username


class SpecialWorkClaimForm(forms.ModelForm):
    """Form for employees to claim special leave credits for working beyond normal hours"""
    
    work_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px;'
        }),
        help_text="Start date when you worked beyond normal working hours"
    )
    
    work_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px;'
        }),
        help_text="End date for consecutive work days (leave blank for single day)"
    )

    class Meta:
        model = SpecialWorkClaim
        fields = ['work_date', 'work_end_date', 'session', 'event_name', 'description', 'priority']
        
        widgets = {
            'session': forms.Select(attrs={
                'class': 'form-control',
                'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px;'
            }),
            'event_name': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px;',
                'placeholder': 'e.g., Weekend project deployment, Holiday system maintenance...'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px;',
                'placeholder': 'Describe the work performed and why it was necessary...'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-control',
                'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px;'
            })
        }

    def __init__(self, *args, **kwargs):
        self.employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        
        # Set default values
        if not self.instance.pk:
            self.fields['work_date'].initial = date.today()
            self.fields['session'].initial = 'FULL'
            self.fields['priority'].initial = 'normal'

    def clean_work_date(self):
        work_date = self.cleaned_data.get('work_date')
        
        if work_date:
            # Check if date is not in the future
            if work_date > date.today():
                raise forms.ValidationError("Work date cannot be in the future.")
            
            # Check if date is not too old (e.g., more than 6 months ago)
            six_months_ago = date.today() - timedelta(days=180)
            if work_date < six_months_ago:
                raise forms.ValidationError("Work date cannot be more than 6 months ago.")
                
        return work_date

    def clean_work_end_date(self):
        work_end_date = self.cleaned_data.get('work_end_date')
        
        if work_end_date:
            # Check if end date is not in the future
            if work_end_date > date.today():
                raise forms.ValidationError("Work end date cannot be in the future.")
            
            # Check if end date is not too old
            six_months_ago = date.today() - timedelta(days=180)
            if work_end_date < six_months_ago:
                raise forms.ValidationError("Work end date cannot be more than 6 months ago.")
                
        return work_end_date

    def clean(self):
        cleaned_data = super().clean()
        work_date = cleaned_data.get('work_date')
        work_end_date = cleaned_data.get('work_end_date')
        session = cleaned_data.get('session')
        
        # Validate date range
        if work_date and work_end_date:
            if work_end_date < work_date:
                raise forms.ValidationError("End date cannot be before start date.")
            
            # Limit to reasonable range (e.g., max 14 days)
            if (work_end_date - work_date).days > 13:  # 14 days max
                raise forms.ValidationError("Work claim period cannot exceed 14 consecutive days.")
        
        # Set work_end_date to work_date if not provided (single day)
        if work_date and not work_end_date:
            cleaned_data['work_end_date'] = work_date
        
        if work_date and session and self.employee:
            # Check for overlapping claims
            from django.db.models import Q
            start_date = work_date
            end_date = work_end_date or work_date
            
            overlapping_claims = SpecialWorkClaim.objects.filter(
                employee=self.employee,
                session=session,
                status__in=['pending', 'approved']
            ).filter(
                Q(work_date__lte=end_date, work_end_date__gte=start_date) |
                Q(work_date__lte=end_date, work_end_date__isnull=True, work_date__gte=start_date)
            )
            
            # Exclude current instance if editing
            if self.instance.pk:
                overlapping_claims = overlapping_claims.exclude(pk=self.instance.pk)
            
            if overlapping_claims.exists():
                existing_claim = overlapping_claims.first()
                raise forms.ValidationError(
                    f"You have overlapping {existing_claim.status} claims for {session} session in this date range."
                    )
        
        return cleaned_data


class SpecialLeaveApplicationForm(forms.ModelForm):
    """Form for employees to apply for special leave using earned credits"""
    
    leave_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px;'
        }),
        help_text="Start date for which you want to apply special leave"
    )
    
    leave_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'style': 'width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px;'
        }),
        help_text="End date for consecutive leave days (leave blank for single day)"
    )

    class Meta:
        model = SpecialLeaveApplication
        fields = ['leave_date', 'leave_end_date', 'session', 'reason', 'urgency']


class BatchApprovalForm(forms.Form):
    """Form for batch approval/rejection of special work claims and leave applications"""
    ACTION_CHOICES = (
        ('approve', 'Approve Selected'),
        ('reject', 'Reject Selected'),
    )
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'style': 'width: auto; display: inline-block;'
        })
    )
    
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Optional comment for all selected items...'
        }),
        help_text="This comment will be applied to all selected items"
    )
    
    # Hidden fields for selected items
    selected_claims = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    selected_applications = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        selected_claims = cleaned_data.get('selected_claims', '')
        selected_applications = cleaned_data.get('selected_applications', '')
        
        # Ensure at least one item is selected
        if not selected_claims and not selected_applications:
            raise forms.ValidationError("Please select at least one item to process.")
        
        # Require comment for rejection
        if action == 'reject' and not cleaned_data.get('comment'):
            raise forms.ValidationError("Comment is required when rejecting items.")
        
        return cleaned_data


class ManagerCommentForm(forms.Form):
    """Form for adding manager comments to special leave items"""
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'form-control',
            'placeholder': 'Add your manager comment here...'
        }),
        help_text="This comment will be visible to the employee"
    )
    
    action = forms.CharField(widget=forms.HiddenInput())
    item_type = forms.CharField(widget=forms.HiddenInput())
    item_id = forms.CharField(widget=forms.HiddenInput())