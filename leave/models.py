from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, datetime, time
from decimal import Decimal

class EmployeeProfile(models.Model):
    REGION_CHOICES = (
        ('HK', 'Hong Kong'),
        ('CN', 'China Mainland'),
    )
    
    COMPANY_CHOICES = (
        ('Krystal Institute Ltd', 'Krystal Institute Ltd'),
        ('Krystal Technology Ltd', 'Krystal Technology Ltd'),
        ('Other', 'Other'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_joined = models.DateField()
    region = models.CharField(max_length=2, choices=REGION_CHOICES, default='HK')
    company = models.CharField(max_length=100, choices=COMPANY_CHOICES, default='Krystal Institute Ltd')

    def years_of_service(self):
        return round((date.today() - self.date_joined).days / 365, 2)

    def get_leave_balance(self, leave_type_name, year=None):
        """Get current leave balance for a specific leave type"""
        if year is None:
            year = date.today().year
        try:
            leave_type = LeaveType.objects.get(name=leave_type_name)
            balance = LeaveBalance.objects.get(
                employee=self, 
                leave_type=leave_type, 
                year=year
            )
            return balance
        except (LeaveType.DoesNotExist, LeaveBalance.DoesNotExist):
            return None

    def get_annual_leave_entitlement(self, year=None):
        """Calculate annual leave entitlement based on years of service"""
        if year is None:
            year = date.today().year
        years = self.years_of_service()
        
        # Standard entitlement calculation (adjust as per company policy)
        if years < 1:
            return Decimal('0.00')
        elif years < 5:
            return Decimal('14.00')  # 14 days for 1-5 years
        elif years < 10:
            return Decimal('18.00')  # 18 days for 5-10 years
        else:
            return Decimal('21.00')  # 21 days for 10+ years

    def get_detailed_annual_leave_balance(self, year=None):
        """Get detailed annual leave balance information"""
        if year is None:
            year = date.today().year
        
        try:
            annual_leave_type = LeaveType.objects.get(name='Annual Leave')
            balance = LeaveBalance.objects.get(
                employee=self, 
                leave_type=annual_leave_type, 
                year=year
            )
            
            # Calculate taken this year from Jan 1
            from django.db.models import Sum
            taken_from_jan = LeaveApplication.objects.filter(
                employee=self,
                leave_type=annual_leave_type,
                status='approved',
                date_from__year=year,
                date_from__gte=date(year, 1, 1)
            ).aggregate(total=Sum('days_applied'))['total'] or Decimal('0.00')
            
            return {
                'carried_forward': balance.carried_forward,
                'current_year_entitlement': balance.current_year_entitlement,
                'taken_this_year': taken_from_jan,
                'current_balance': balance.balance,
                'total_available': balance.carried_forward + balance.current_year_entitlement
            }
            
        except (LeaveType.DoesNotExist, LeaveBalance.DoesNotExist):
            return {
                'carried_forward': Decimal('0.00'),
                'current_year_entitlement': self.get_annual_leave_entitlement(year),
                'taken_this_year': Decimal('0.00'),
                'current_balance': self.get_annual_leave_entitlement(year),
                'total_available': self.get_annual_leave_entitlement(year)
            }

    def get_holidays_for_region(self, year):
        """Get holidays for employee's region, combining imported and manual holidays"""
        # First, try to get from our database
        db_holidays = {}
        holiday_objects = PublicHoliday.objects.filter(
            region=self.region, 
            year=year, 
            is_active=True
        )
        
        for holiday in holiday_objects:
            db_holidays[holiday.date] = holiday.name
        
        # If we have holidays in database, return them
        if db_holidays:
            return db_holidays
        
        # Otherwise, import from holidays library and save to database
        try:
            import holidays
            
            if self.region == 'HK':
                region_holidays = holidays.HongKong(years=year)
            elif self.region == 'CN':
                region_holidays = holidays.China(years=year)
            else:
                return {}
            
            # Save imported holidays to database for future manual editing
            for date, name in region_holidays.items():
                PublicHoliday.objects.get_or_create(
                    date=date,
                    region=self.region,
                    defaults={
                        'name': name,
                        'year': date.year,
                        'is_active': True,
                        'is_imported': True
                    }
                )
            
            return dict(region_holidays)
            
        except ImportError:
            # If holidays library is not available, return empty dict
            return {}

    def get_special_leave_balance(self, as_of_date=None):
        """Calculate special leave balance (earned credits - used credits)"""
        if as_of_date is None:
            as_of_date = date.today()
        
        # Get total credits earned from approved special work claims
        earned_credits = SpecialWorkClaim.objects.filter(
            employee=self,
            status='approved',
            work_date__lte=as_of_date
        ).aggregate(
            total=models.Sum('credits_earned')
        )['total'] or Decimal('0.00')
        
        # Get total credits used from approved special leave applications
        used_credits = SpecialLeaveApplication.objects.filter(
            employee=self,
            status='approved',
            leave_date__lte=as_of_date
        ).aggregate(
            total=models.Sum('credits_used')
        )['total'] or Decimal('0.00')
        
        balance = earned_credits - used_credits
        
        return {
            'earned': earned_credits,
            'used': used_credits,
            'balance': balance
        }

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.email}) - {self.get_region_display()}"

class LeaveType(models.Model):
    name = models.CharField(max_length=64)  # Annual, Sick, No Paid, Special

    def __str__(self):
        return self.name

def get_current_year():
    return date.today().year

class LeaveBalance(models.Model):
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.IntegerField(default=get_current_year)
    opening_balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    carried_forward = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    current_year_entitlement = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    taken = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = ['employee', 'leave_type', 'year']

    def calculate_balance(self):
        """Calculate and update the current balance"""
        # Calculate taken leaves for this year
        taken_this_year = LeaveApplication.objects.filter(
            employee=self.employee,
            leave_type=self.leave_type,
            status='approved',
            date_from__year=self.year
        ).aggregate(total=models.Sum('days_applied'))['total'] or Decimal('0.00')
        
        self.taken = taken_this_year
        self.balance = self.opening_balance + self.carried_forward + self.current_year_entitlement - self.taken
        return self.balance

    def save(self, *args, **kwargs):
        """Auto-calculate balance before saving"""
        self.calculate_balance()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} - {self.leave_type} {self.year} ({self.balance})"

class LeaveApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    )
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    date_from = models.DateTimeField()
    date_to = models.DateTimeField()
    days_applied = models.DecimalField(max_digits=4, decimal_places=2)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    approver = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_leaves')
    manager_comment = models.TextField(blank=True)
    certificate = models.FileField(upload_to='sick_certificates/', blank=True, null=True)  # For sick leave
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    includes_saturday_work = models.BooleanField(default=False)
    saturday_work_days = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    def calculate_leave_days(self):
        """Calculate leave days considering holidays, weekends, and Saturday working day policy"""
        from datetime import timedelta
        
        # Safety check for employee
        if not self.employee:
            raise ValueError("LeaveApplication must have an employee to calculate leave days")
        
        start_date = self.date_from.date()
        end_date = self.date_to.date()
        start_time = self.date_from.time()
        end_time = self.date_to.time()
        
        # Get holidays for employee's region
        region_holidays = self.employee.get_holidays_for_region(start_date.year)
        if start_date.year != end_date.year:
            # Add holidays for the end year if different
            region_holidays.update(self.employee.get_holidays_for_region(end_date.year))
        
        # Handle same day leave applications
        if start_date == end_date:
            # Same day application
            if start_date.weekday() < 5 and start_date not in region_holidays:  # Weekday and not holiday
                # Determine if it's half day or full day based on time
                
                # AM session: 9:00-13:00, PM session: 13:00-18:00
                if start_time == time(9, 0) and end_time == time(13, 0):
                    # AM only - half day
                    business_days = 0.5
                elif start_time == time(13, 0) and end_time == time(18, 0):
                    # PM only - half day
                    business_days = 0.5
                elif start_time == time(9, 0) and end_time == time(18, 0):
                    # Full day AM to PM
                    business_days = 1.0
                else:
                    # Default calculation for other time combinations
                    business_days = 0.5  # Assume half day for non-standard times
                
                # Count Friday for Saturday working day policy
                friday_count = 1 if start_date.weekday() == 4 else 0
            else:
                # Weekend or holiday - no business days
                business_days = 0
                friday_count = 0
        else:
            # Multi-day application - calculate each day
            current_date = start_date
            business_days = 0
            friday_count = 0
            
            while current_date <= end_date:
                # Check if it's a weekday (Monday=0, Sunday=6)
                if current_date.weekday() < 5:  # Monday to Friday
                    # Check if it's not a holiday
                    if current_date not in region_holidays:
                        if current_date == start_date:
                            # First day - check start time
                            if start_time == time(9, 0):
                                business_days += 1.0  # Full day from AM
                            elif start_time == time(13, 0):
                                business_days += 0.5  # Half day from PM
                            else:
                                business_days += 0.5  # Default for other start times
                        elif current_date == end_date:
                            # Last day - check end time
                            if end_time == time(18, 0):
                                business_days += 1.0  # Full day to PM
                            elif end_time == time(13, 0):
                                business_days += 0.5  # Half day to AM end
                            else:
                                business_days += 0.5  # Default for other end times
                        else:
                            # Middle days - always full days
                            business_days += 1.0
                        
                        # Count Fridays for Saturday working day policy
                        if current_date.weekday() == 4:  # Friday
                            friday_count += 1
                
                current_date += timedelta(days=1)
        
        # Apply Saturday working day policy: +1 day for each Friday (Saturday is counted as working day)
        saturday_work_days = friday_count
        total_days = business_days + saturday_work_days
        
        # Store Saturday working day information
        self.includes_saturday_work = friday_count > 0
        self.saturday_work_days = saturday_work_days
        
        return total_days

    def get_holiday_info(self):
        """Get holiday information for the leave period"""
        from datetime import timedelta
        
        start_date = self.date_from.date()
        end_date = self.date_to.date()
        
        region_holidays = self.employee.get_holidays_for_region(start_date.year)
        if start_date.year != end_date.year:
            region_holidays.update(self.employee.get_holidays_for_region(end_date.year))
        
        holidays_in_period = []
        current_date = start_date
        
        while current_date <= end_date:
            if current_date in region_holidays:
                holidays_in_period.append({
                    'date': current_date.strftime('%Y-%m-%d'),  # Convert to string for JSON serialization
                    'name': region_holidays[current_date]
                })
            current_date += timedelta(days=1)
        
        return holidays_in_period

    def save(self, *args, **kwargs):
        """Auto-calculate days when saving"""
        if self.date_from and self.date_to:
            self.days_applied = self.calculate_leave_days()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} - {self.leave_type} [{self.status}]"

class SpecialWorkClaim(models.Model):
    """Model for employees to claim special leave credits by working beyond normal working days"""
    SESSION_CHOICES = (
        ('AM', 'AM (9:00 - 13:00)'),
        ('PM', 'PM (13:00 - 18:00)'),
        ('FULL', 'Full Day (9:00 - 18:00)'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    work_date = models.DateField(help_text="Start date when extra work was performed")
    work_end_date = models.DateField(null=True, blank=True, help_text="End date for consecutive work days (leave blank for single day)")
    session = models.CharField(max_length=4, choices=SESSION_CHOICES, default='FULL')
    event_name = models.CharField(max_length=255, help_text="Name of the event or reason for working beyond normal hours")
    description = models.TextField(blank=True, help_text="Additional details about the work performed")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal', help_text="Priority level of the work performed")
    
    # Automatically calculated based on session
    credits_earned = models.DecimalField(max_digits=4, decimal_places=2, default=0, 
                                       help_text="Special leave credits earned (0.5 for AM/PM, 1.0 for Full Day)")
    
    status = models.CharField(max_length=16, choices=LeaveApplication.STATUS_CHOICES, default='pending')
    approver = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_claims')
    manager_comment = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True, help_text="Detailed reason for rejection if applicable")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True, help_text="Date and time when approved")
    
    # Notification tracking
    employee_notified = models.BooleanField(default=False, help_text="Whether employee has been notified of status change")
    notification_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-work_date', '-created_at']
        unique_together = ['employee', 'work_date', 'session']  # Prevent duplicate claims for same date/session
        indexes = [
            models.Index(fields=['status', 'work_date']),
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['priority', 'created_at']),
        ]

    def get_work_days_count(self):
        """Calculate number of work days in the claim period"""
        start_date = self.work_date
        end_date = self.work_end_date or self.work_date
        
        from datetime import timedelta
        days_count = 0
        current_date = start_date
        
        while current_date <= end_date:
            # Count all days in the range (including weekends for special work)
            days_count += 1
            current_date += timedelta(days=1)
            
        return days_count

    def save(self, *args, **kwargs):
        """Auto-calculate credits based on session and date range, set approval timestamp"""
        # Calculate base credits per day
        credits_per_day = Decimal('0.5') if self.session in ['AM', 'PM'] else Decimal('1.0')
        
        # Calculate total credits for all days in range
        days_count = self.get_work_days_count()
        self.credits_earned = credits_per_day * days_count
        
        # Set approved_at timestamp if status is being changed to approved
        if self.pk:
            old_instance = SpecialWorkClaim.objects.get(pk=self.pk)
            if old_instance.status != 'approved' and self.status == 'approved':
                self.approved_at = timezone.now()
        elif self.status == 'approved':
            self.approved_at = timezone.now()
            
        super().save(*args, **kwargs)

    def get_priority_badge_class(self):
        """Get Bootstrap badge class for priority display"""
        priority_classes = {
            'low': 'badge-secondary',
            'normal': 'badge-info', 
            'high': 'badge-warning',
            'urgent': 'badge-danger'
        }
        return priority_classes.get(self.priority, 'badge-info')

    def can_be_edited(self):
        """Check if claim can still be edited by employee"""
        return self.status == 'pending'

    def can_be_withdrawn(self):
        """Check if claim can be withdrawn by employee"""
        return self.status == 'pending'

    def __str__(self):
        if self.work_end_date and self.work_end_date != self.work_date:
            date_str = f"{self.work_date} to {self.work_end_date}"
        else:
            date_str = str(self.work_date)
        return f"{self.employee} - {self.event_name} ({self.get_session_display()}) {date_str} [{self.get_status_display()}]"


class SpecialLeaveApplication(models.Model):
    """Model for employees to apply for special leave using their earned credits"""
    SESSION_CHOICES = (
        ('AM', 'AM (9:00 - 13:00)'),
        ('PM', 'PM (13:00 - 18:00)'),
        ('FULL', 'Full Day (9:00 - 18:00)'),
    )
    
    URGENCY_CHOICES = (
        ('low', 'Low - Can wait for approval'),
        ('normal', 'Normal - Standard processing'),
        ('high', 'High - Need approval soon'),
        ('urgent', 'Urgent - Need immediate approval'),
    )
    
    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    leave_date = models.DateField(help_text="Start date for which special leave is requested")
    leave_end_date = models.DateField(null=True, blank=True, help_text="End date for consecutive leave days (leave blank for single day)")
    session = models.CharField(max_length=4, choices=SESSION_CHOICES, default='FULL')
    reason = models.TextField(help_text="Reason for special leave application")
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='normal', help_text="Urgency level of this leave request")
    
    # Automatically calculated based on session
    credits_used = models.DecimalField(max_digits=4, decimal_places=2, default=0,
                                     help_text="Special leave credits used (0.5 for AM/PM, 1.0 for Full Day)")
    
    status = models.CharField(max_length=16, choices=LeaveApplication.STATUS_CHOICES, default='pending')
    approver = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_special_leaves')
    manager_comment = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True, help_text="Detailed reason for rejection if applicable")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True, help_text="Date and time when approved")
    
    # Notification tracking
    employee_notified = models.BooleanField(default=False, help_text="Whether employee has been notified of status change")
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Auto-withdrawal for past dates
    auto_withdrawn = models.BooleanField(default=False, help_text="Automatically withdrawn if leave date has passed")

    class Meta:
        ordering = ['-leave_date', '-created_at']
        unique_together = ['employee', 'leave_date', 'session']  # Prevent duplicate applications for same date/session
        indexes = [
            models.Index(fields=['status', 'leave_date']),
            models.Index(fields=['employee', 'status']),
            models.Index(fields=['urgency', 'created_at']),
            models.Index(fields=['leave_date', 'status']),
        ]

    def get_leave_days_count(self):
        """Calculate number of leave days in the application period"""
        start_date = self.leave_date
        end_date = self.leave_end_date or self.leave_date
        
        from datetime import timedelta
        days_count = 0
        current_date = start_date
        
        while current_date <= end_date:
            # Count all days in the range
            days_count += 1
            current_date += timedelta(days=1)
            
        return days_count

    def save(self, *args, **kwargs):
        """Auto-calculate credits used based on session and date range, set approval timestamp"""
        # Calculate base credits per day
        credits_per_day = Decimal('0.5') if self.session in ['AM', 'PM'] else Decimal('1.0')
        
        # Calculate total credits for all days in range
        days_count = self.get_leave_days_count()
        self.credits_used = credits_per_day * days_count
        
        # Set approved_at timestamp if status is being changed to approved
        if self.pk:
            old_instance = SpecialLeaveApplication.objects.get(pk=self.pk)
            if old_instance.status != 'approved' and self.status == 'approved':
                self.approved_at = timezone.now()
        elif self.status == 'approved':
            self.approved_at = timezone.now()
        
        # Auto-withdraw if leave date has passed and still pending
        if self.leave_date < date.today() and self.status == 'pending':
            self.status = 'withdrawn'
            self.auto_withdrawn = True
            
        super().save(*args, **kwargs)

    def get_urgency_badge_class(self):
        """Get Bootstrap badge class for urgency display"""
        urgency_classes = {
            'low': 'badge-secondary',
            'normal': 'badge-info', 
            'high': 'badge-warning',
            'urgent': 'badge-danger'
        }
        return urgency_classes.get(self.urgency, 'badge-info')

    def can_be_edited(self):
        """Check if application can still be edited by employee"""
        return self.status == 'pending' and self.leave_date >= date.today()

    def can_be_withdrawn(self):
        """Check if application can be withdrawn by employee"""
        return self.status == 'pending' and self.leave_date >= date.today()

    def is_urgent(self):
        """Check if this is an urgent application needing immediate attention"""
        return self.urgency == 'urgent'

    def days_until_leave(self):
        """Calculate days until leave date"""
        if self.leave_date < date.today():
            return 0
        return (self.leave_date - date.today()).days

    def __str__(self):
        if self.leave_end_date and self.leave_end_date != self.leave_date:
            date_str = f"{self.leave_date} to {self.leave_end_date}"
        else:
            date_str = str(self.leave_date)
        return f"{self.employee} - Special Leave ({self.get_session_display()}) {date_str} [{self.get_status_display()}]"


class SpecialLeaveNotification(models.Model):
    """Model for tracking notifications and workflow actions for special leave system"""
    NOTIFICATION_TYPES = (
        ('claim_submitted', 'Work Claim Submitted'),
        ('claim_approved', 'Work Claim Approved'),
        ('claim_rejected', 'Work Claim Rejected'),
        ('application_submitted', 'Leave Application Submitted'),
        ('application_approved', 'Leave Application Approved'),
        ('application_rejected', 'Leave Application Rejected'),
        ('application_auto_withdrawn', 'Application Auto-Withdrawn'),
        ('reminder_approval_needed', 'Approval Reminder'),
        ('urgent_approval_needed', 'Urgent Approval Needed'),
    )
    
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='special_leave_notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_special_leave_notifications', null=True, blank=True)
    
    # Reference to the related object
    work_claim = models.ForeignKey(SpecialWorkClaim, on_delete=models.CASCADE, null=True, blank=True)
    leave_application = models.ForeignKey(SpecialLeaveApplication, on_delete=models.CASCADE, null=True, blank=True)
    
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} to {self.recipient.get_full_name()}"


class SpecialLeaveApprovalWorkflow(models.Model):
    """Model for tracking approval workflow and audit trail"""
    ACTION_TYPES = (
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
        ('edited', 'Edited'),
        ('comment_added', 'Comment Added'),
        ('priority_changed', 'Priority Changed'),
        ('urgency_changed', 'Urgency Changed'),
    )
    
    # Reference to the related object
    work_claim = models.ForeignKey(SpecialWorkClaim, on_delete=models.CASCADE, null=True, blank=True, related_name='workflow_history')
    leave_application = models.ForeignKey(SpecialLeaveApplication, on_delete=models.CASCADE, null=True, blank=True, related_name='workflow_history')
    
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    performed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Additional metadata
    old_status = models.CharField(max_length=16, blank=True)
    new_status = models.CharField(max_length=16, blank=True)
    metadata = models.JSONField(default=dict, blank=True)  # For storing additional data
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        item_type = "Work Claim" if self.work_claim else "Leave Application"
        return f"{item_type} {self.get_action_display()} by {self.performed_by.get_full_name()}"


class PublicHoliday(models.Model):
    """Model to store and manage public holidays"""
    REGION_CHOICES = [
        ('HK', 'Hong Kong'),
        ('CN', 'China'),
    ]
    
    name = models.CharField(max_length=200)
    date = models.DateField()
    region = models.CharField(max_length=2, choices=REGION_CHOICES)
    year = models.IntegerField()
    is_active = models.BooleanField(default=True)
    is_imported = models.BooleanField(default=True, help_text="True if imported from holidays library, False if manually added")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['date', 'region']
        ordering = ['year', 'date']
    
    def __str__(self):
        return f"{self.name} ({self.get_region_display()}) - {self.date}"


class EmployeeImportRecord(models.Model):
    """Track employee CSV import history"""
    IMPORT_STATUS_CHOICES = [
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('failed', 'Failed'),
    ]
    
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employee_imports')
    file_name = models.CharField(max_length=255)
    file_content = models.TextField()  # Store the original CSV content
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=IMPORT_STATUS_CHOICES)
    
    # Import statistics
    total_rows = models.IntegerField(default=0)
    created_count = models.IntegerField(default=0)
    updated_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    
    # Detailed results
    import_log = models.TextField(blank=True)  # Store detailed import results
    
    class Meta:
        ordering = ['-upload_date']
    
    def __str__(self):
        return f"{self.file_name} by {self.uploaded_by.username} on {self.upload_date.strftime('%Y-%m-%d %H:%M')}"
    
    def get_status_display_color(self):
        """Return Bootstrap color class for status"""
        if self.status == 'success':
            return 'success'
        elif self.status == 'partial':
            return 'warning'
        else:
            return 'danger'