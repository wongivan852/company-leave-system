from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from django.utils import timezone

class Employee(models.Model):
    REGION_CHOICES = [
        ('HK', 'Hong Kong'),
        ('CN', 'China'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    company = models.CharField(max_length=100, default="Krystal Institute Ltd")
    date_joined = models.DateField(null=True, blank=True)
    region = models.CharField(max_length=2, choices=REGION_CHOICES, default='HK')
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"
    
    class Meta:
        ordering = ['user__last_name', 'user__first_name']

class LeaveType(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    max_days_per_year = models.PositiveIntegerField(default=0)
    requires_approval = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class LeaveApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    date_from = models.DateTimeField()
    date_to = models.DateTimeField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    def calculate_days(self):
        """Calculate the number of leave days based on session logic"""
        if not self.date_from or not self.date_to:
            return 0
        
        # Get the session info from time components
        start_time = self.date_from.time()
        end_time = self.date_to.time()
        
        # Determine if it's AM (9:00) or PM (14:00) sessions
        is_start_am = start_time.hour == 9
        is_start_pm = start_time.hour == 14
        is_end_am = end_time.hour == 13  # End of AM session
        is_end_pm = end_time.hour == 18  # End of PM session
        
        # If same day
        if self.date_from.date() == self.date_to.date():
            if is_start_am and is_end_pm:
                return 1.0  # Full day (AM + PM)
            else:
                return 0.5  # Half day (AM only or PM only)
        
        # Multiple days - count business days and adjust for partial days
        from datetime import timedelta
        total_days = 0
        current_date = self.date_from.date()
        end_date = self.date_to.date()
        
        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday=0, Friday=4
                if current_date == self.date_from.date():
                    # First day - depends on start session
                    total_days += 0.5 if is_start_pm else 1.0
                elif current_date == self.date_to.date():
                    # Last day - depends on end session  
                    total_days += 0.5 if is_end_am else 1.0
                else:
                    # Full middle days
                    total_days += 1.0
            current_date += timedelta(days=1)
            
        return total_days
    
    @property
    def days_applied(self):
        return self.calculate_days()
    
    @property
    def back_to_office_date(self):
        """Calculate when employee should return to office"""
        if not self.date_from:
            return None
            
        # If leave starts in AM (9:00), return same day
        if self.date_from.time().hour == 9:
            return self.date_from.date()
        
        # If leave is PM only, return next working day
        from datetime import timedelta
        next_day = self.date_to.date() + timedelta(days=1)
        # Skip weekends (basic logic - could be enhanced)
        while next_day.weekday() >= 5:  # Saturday=5, Sunday=6
            next_day += timedelta(days=1)
        return next_day
    
    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.get_status_display()})"
    
    def can_cancel(self):
        """Check if the leave application can be cancelled."""
        from django.utils import timezone
        return (self.status == 'pending' and 
                self.date_from > timezone.now().date())
    
    class Meta:
        ordering = ['-created_at']


class SpecialWorkClaim(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    SESSION_CHOICES = [
        ('AM', 'AM (9:00am - 1:00pm)'),
        ('PM', 'PM (2:00pm - 6:00pm)'),
        ('FULL', 'Full Day (9:00am - 6:00pm)'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    work_date = models.DateField()
    work_end_date = models.DateField(null=True, blank=True, help_text="Leave blank for single day")
    session = models.CharField(max_length=10, choices=SESSION_CHOICES)
    event_name = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    credits_earned = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_special_work')
    approved_at = models.DateTimeField(null=True, blank=True)
    manager_comment = models.TextField(blank=True)
    
    def get_work_days_count(self):
        """Calculate the number of work days"""
        if not self.work_end_date or self.work_end_date == self.work_date:
            return 1
        return (self.work_end_date - self.work_date).days + 1
    
    def calculate_credits(self):
        """Calculate credits based on session and work days"""
        days = self.get_work_days_count()
        if self.session == 'FULL':
            return float(days)
        else:  # AM or PM
            return float(days * 0.5)
    
    def save(self, *args, **kwargs):
        # Auto-calculate credits
        self.credits_earned = self.calculate_credits()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.employee} - {self.event_name} ({self.work_date})"
    
    class Meta:
        ordering = ['-created_at']

class SpecialLeaveApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date_from = models.DateTimeField()
    date_to = models.DateTimeField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    credits_used = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_special_leaves')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    def calculate_days(self):
        """Calculate the number of leave days based on session logic (same as regular leave)"""
        if not self.date_from or not self.date_to:
            return 0
        
        # Get the session info from time components
        start_time = self.date_from.time()
        end_time = self.date_to.time()
        
        # Determine if it's AM (9:00) or PM (14:00) sessions
        is_start_am = start_time.hour == 9
        is_start_pm = start_time.hour == 14
        is_end_am = end_time.hour == 13  # End of AM session
        is_end_pm = end_time.hour == 18  # End of PM session
        
        # If same day
        if self.date_from.date() == self.date_to.date():
            if is_start_am and is_end_pm:
                return 1.0  # Full day (AM + PM)
            else:
                return 0.5  # Half day (AM only or PM only)
        
        # Multiple days - count business days and adjust for partial days
        from datetime import timedelta
        total_days = 0
        current_date = self.date_from.date()
        end_date = self.date_to.date()
        
        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday=0, Friday=4
                if current_date == self.date_from.date():
                    # First day - depends on start session
                    total_days += 0.5 if is_start_pm else 1.0
                elif current_date == self.date_to.date():
                    # Last day - depends on end session  
                    total_days += 0.5 if is_end_am else 1.0
                else:
                    # Full middle days
                    total_days += 1.0
            current_date += timedelta(days=1)
            
        return total_days
    
    @property
    def days_applied(self):
        return self.calculate_days()
    
    @property
    def back_to_office_date(self):
        """Calculate when employee should return to office"""
        if not self.date_from:
            return None
            
        # If leave starts in AM (9:00), return same day
        if self.date_from.time().hour == 9:
            return self.date_from.date()
        
        # If leave is PM only, return next working day
        from datetime import timedelta
        next_day = self.date_to.date() + timedelta(days=1)
        # Skip weekends (basic logic - could be enhanced)
        while next_day.weekday() >= 5:  # Saturday=5, Sunday=6
            next_day += timedelta(days=1)
        return next_day
    
    def save(self, *args, **kwargs):
        # Auto-calculate credits used
        self.credits_used = self.calculate_days()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.employee} - Special Leave ({self.get_status_display()})"
    
    class Meta:
        ordering = ['-created_at']

class SpecialLeaveBalance(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='special_leave_balance')
    earned = models.FloatField(default=0.0, help_text="Credits earned from special work claims")
    used = models.FloatField(default=0.0, help_text="Credits used for special leave")
    year = models.IntegerField(default=2025)
    
    @property
    def balance(self):
        return self.earned - self.used
    
    def __str__(self):
        return f"{self.employee} - Special Leave Balance: {self.balance}"
    
    class Meta:
        ordering = ['employee__user__last_name']
        unique_together = ['employee', 'year']

class PendingRegistration(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    LOCATION_CHOICES = [
        ('HK', 'Hong Kong'),
        ('CN', 'China'),
        ('OTHER', 'Other'),
    ]
    
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    other_name = models.CharField(max_length=50, blank=True)
    office_location = models.CharField(max_length=10, choices=LOCATION_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email}) - {self.status}"
    
    class Meta:
        ordering = ['-created_at']
