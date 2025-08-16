from django.urls import path
from django.shortcuts import redirect
from . import views, views_auth

app_name = "leave"

def redirect_to_dashboard(request):
    return redirect('leave:dashboard')

urlpatterns = [
    path("", redirect_to_dashboard, name="home"),
    path("login/", views_auth.CustomLoginView.as_view(), name="login"),
    path("logout/", views_auth.CustomLogoutView.as_view(), name="logout"),
    path("register/", views_auth.register, name="register"),
    path("dashboard/", views_auth.dashboard, name="dashboard"),
    path("apply-leave/", views.apply_leave, name="apply_leave"),
    path("apply-leave/confirm/<int:application_id>/", views.apply_leave_confirm, name="apply_leave_confirm"),
    path("leave-applications/", views.leave_applications, name="leave_applications"),
    path("leave-applications/<int:application_id>/", views.leave_application_detail, name="leave_application_detail"),
    path("leave-applications/<int:application_id>/revise/", views.revise_leave_application, name="revise_leave_application"),
    path("leave-applications/<int:application_id>/withdraw/", views.withdraw_leave_application, name="withdraw_leave_application"),
    path("holidays/", views.holiday_management, name="holiday_management"),
    path("holidays/import/", views.holiday_import, name="holiday_import"),
    path("holidays/add/", views.holiday_add, name="holiday_add"),
    path("employees/import/", views.employee_import, name="employee_import"),
    path("employees/import/history/", views.import_history, name="import_history"),
    path("employees/import/<int:import_id>/view/", views.view_import_content, name="view_import_content"),
    path("employees/download-balances/", views.download_balances, name="download_balances"),
    path("special-work-claim/", views.special_work_claim, name="special_work_claim"),
    path("special-leave-apply/", views.special_leave_apply, name="special_leave_apply"),
    path("special-leave-apply/confirm/<int:application_id>/", views.special_leave_apply_confirm, name="special_leave_apply_confirm"),
    path("special-leave-management/", views.special_leave_management, name="special_leave_management"),
    path("holidays/<int:holiday_id>/edit/", views.holiday_edit, name="holiday_edit"),
    path("holidays/<int:holiday_id>/delete/", views.holiday_delete, name="holiday_delete"),
    path("leave-applications/<int:application_id>/print/", views.leave_form_print, name="leave_form_print"),
    path("leave-applications/<int:application_id>/pdf/", views.leave_form_pdf, name="leave_form_pdf"),
    path("leave-applications/combined/print/", views.combined_print, name="combined_print"),
    path("leave-applications/combined/pdf/", views.combined_print_pdf, name="combined_print_pdf"),
    # Manager approval URLs
    path("manager/", views.manager_dashboard, name="manager_dashboard"),
    path("manager/approve-leave/<int:application_id>/", views.approve_leave_application, name="approve_leave_application"),
    path("manager/approve-claim/<int:claim_id>/", views.approve_special_work_claim, name="approve_special_work_claim"),
    path("manager/approve-special-leave/<int:application_id>/", views.approve_special_leave_application, name="approve_special_leave_application"),
]