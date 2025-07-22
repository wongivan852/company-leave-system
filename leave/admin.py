from django.contrib import admin
from .models import EmployeeProfile, LeaveType, LeaveBalance, LeaveApplication, SpecialWorkClaim, SpecialLeaveApplication

admin.site.register(EmployeeProfile)
admin.site.register(LeaveType)
admin.site.register(LeaveBalance)
admin.site.register(LeaveApplication)
admin.site.register(SpecialWorkClaim)
admin.site.register(SpecialLeaveApplication)