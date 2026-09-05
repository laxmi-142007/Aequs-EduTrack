"""
Views for RBAC: admin portal, employee dashboard, user management.
"""
import csv
import json
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, Permission
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from academics.models import AcademicRecord
from distributions.models import Distribution
from eligibility.models import EligibilityRecord
from internships.models import InternshipPlacement
from inventory.models import Laptop, LaptopAssignment
from schools.models import School
from students.models import Student
from volunteers.models import Volunteer
from events.models import Event

from .decorators import admin_required, employee_required
from .forms import (
    AdminUserChangeForm,
    AdminUserCreationForm,
    PasswordChangeOnFirstLoginForm,
    SystemRoleCreationForm,
)
from .models import User, SystemRole


# ================================================================
# PASSWORD CHANGE ON FIRST LOGIN
# ================================================================

@login_required
def force_password_change(request):
    """View for users to change their password on first login."""
    if not request.user.must_change_password:
        return redirect("accounts:dashboard_redirect")

    if request.method == "POST":
        form = PasswordChangeOnFirstLoginForm(request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data["new_password"])
            request.user.must_change_password = False
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password changed successfully. Welcome to Aequs EduTrack!")
            return redirect("accounts:dashboard_redirect")
    else:
        form = PasswordChangeOnFirstLoginForm()

    return render(request, "accounts/change_password.html", {"form": form})


# ================================================================
# DASHBOARD ROUTING
# ================================================================

@login_required
def dashboard_redirect(request):
    """Redirect users to the appropriate dashboard based on role."""
    if request.user.is_admin:
        return redirect("accounts:admin_dashboard")
    return redirect("accounts:employee_dashboard")


# ================================================================
# ADMIN DASHBOARD
# ================================================================

@admin_required
def admin_dashboard(request):
    """Admin Executive Dashboard with full system overview."""
    context = {
        "total_users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "users_pending_password": User.objects.filter(
            must_change_password=True
        ).count(),
        "school_count": School.objects.filter(
            status=School.Status.ACTIVE
        ).count(),
        "student_count": Student.objects.count(),
        "active_student_count": Student.objects.filter(
            status=Student.Status.ACTIVE
        ).count(),
        "academic_record_count": AcademicRecord.objects.count(),
        "eligible_student_count": EligibilityRecord.objects.filter(
            eligible=True
        ).values("student").distinct().count(),
        "available_laptop_count": Laptop.objects.filter(
            status=Laptop.Status.AVAILABLE
        ).count(),
        "issued_laptop_count": Laptop.objects.filter(
            status=Laptop.Status.ISSUED
        ).count(),
        "internship_count": InternshipPlacement.objects.count(),
        "active_interns_count": InternshipPlacement.objects.filter(
            status__in=[
                InternshipPlacement.Status.SELECTED,
                InternshipPlacement.Status.IN_PROGRESS,
            ]
        ).count(),
        "distribution_count": Distribution.objects.count(),
        "students_benefited_count": Distribution.objects.values(
            "student"
        ).distinct().count(),
        "volunteer_count": Volunteer.objects.filter(status="ACTIVE").count(),
        "recent_eligibility": EligibilityRecord.objects.select_related(
            "student"
        ).order_by("-checked_at")[:10],
        "recent_assignments": LaptopAssignment.objects.select_related(
            "student", "laptop"
        ).order_by("-created_at")[:10],
        "recent_internships": InternshipPlacement.objects.select_related(
            "student", "program"
        ).order_by("-created_at")[:10],
        "recent_distributions": Distribution.objects.select_related(
            "student"
        ).order_by("-distribution_date", "-created_at")[:10],
        "recent_users": User.objects.order_by("-date_joined")[:10],
        "groups": Group.objects.annotate(user_count=Count("user")).order_by("name"),
    }
    return render(request, "accounts/admin_dashboard.html", context)


# ================================================================
# EMPLOYEE DASHBOARD
# ================================================================

@employee_required
def employee_dashboard(request):
    """Employee Dashboard - dynamically tailored based on permissions."""
    user = request.user
    context = {
        "user": user,
        "user_permissions": user.get_all_permissions(),
    }

    if user.has_perm("schools.view_school") or user.is_admin:
        context["school_count"] = School.objects.filter(
            status=School.Status.ACTIVE
        ).count()

    if user.has_perm("students.view_student") or user.is_admin:
        context["student_count"] = Student.objects.count()

    if user.has_perm("academics.view_academicrecord") or user.is_admin:
        context["academic_record_count"] = AcademicRecord.objects.count()

    if user.has_perm("eligibility.view_eligibilityrecord") or user.is_admin:
        context["eligible_student_count"] = EligibilityRecord.objects.filter(
            eligible=True
        ).values("student").distinct().count()

    if user.has_perm("inventory.view_laptop") or user.is_admin:
        context["available_laptop_count"] = Laptop.objects.filter(
            status=Laptop.Status.AVAILABLE
        ).count()

    if user.has_perm("internships.view_internshipplacement") or user.is_admin:
        context["internship_count"] = InternshipPlacement.objects.count()

    if user.has_perm("distributions.view_distribution") or user.is_admin:
        context["distribution_count"] = Distribution.objects.count()

    if user.has_perm("volunteers.view_volunteer") or user.is_admin:
        context["volunteer_count"] = Volunteer.objects.filter(
            status="ACTIVE"
        ).count()

    if user.has_perm("inventory.view_laptopassignment") or user.is_admin:
        context["recent_assignments"] = LaptopAssignment.objects.select_related(
            "student", "laptop"
        ).order_by("-created_at")[:5]

    if user.has_perm("eligibility.view_eligibilityrecord") or user.is_admin:
        context["recent_eligibility"] = EligibilityRecord.objects.select_related(
            "student"
        ).order_by("-checked_at")[:5]

    if getattr(user, "role", "") == "VOLUNTEER" or Volunteer.objects.filter(user=user).exists():
        vol = Volunteer.get_or_create_for_user(user)
        if vol:
            context["is_volunteer_user"] = True
            context["volunteer_profile"] = vol
            context["my_event_participations"] = vol.event_participations.select_related("event").exclude(participation_status="CANCELLED")[:5]

    return render(request, "accounts/employee_dashboard.html", context)


# ================================================================
# USER MANAGEMENT (Admin Only)
# ================================================================

@admin_required
def user_list(request):
    """List all users with advanced search, role, status, and group filters."""
    query = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "").strip()
    status_filter = request.GET.get("status", "").strip()
    group_filter = request.GET.get("group", "").strip()

    users = User.objects.prefetch_related("groups").order_by("-date_joined")

    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )

    if role_filter:
        users = users.filter(role=role_filter)

    if status_filter == "active":
        users = users.filter(is_active=True)
    elif status_filter == "inactive":
        users = users.filter(is_active=False)
    elif status_filter == "pending_pw":
        users = users.filter(must_change_password=True)

    if group_filter:
        if group_filter.isdigit():
            users = users.filter(groups__id=int(group_filter))
        else:
            users = users.filter(groups__name__iexact=group_filter)

    # Context KPI Metrics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = total_users - active_users
    pending_pw_users = User.objects.filter(must_change_password=True).count()
    admin_users = User.objects.filter(
        Q(role__in=[User.Role.ADMIN, User.Role.SUPER_ADMIN]) | Q(is_superuser=True)
    ).distinct().count()

    paginator = Paginator(users, 20)
    page = request.GET.get("page")
    users_page = paginator.get_page(page)

    all_groups = Group.objects.all().order_by("name")

    context = {
        "users": users_page,
        "roles": User.get_all_role_choices(),
        "groups": all_groups,
        "current_role": role_filter,
        "current_status": status_filter,
        "current_group": group_filter,
        "query": query,
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "pending_pw_users": pending_pw_users,
        "admin_users": admin_users,
    }
    return render(request, "accounts/user_list.html", context)


@admin_required
def user_create(request):
    """Admin creates a new user account."""
    if request.method == "POST":
        form = AdminUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f"User '{user.username}' created successfully. "
                + ("They will be required to change their password on first login." if user.must_change_password else ""),
            )
            return redirect("accounts:user_list")
    else:
        form = AdminUserCreationForm()

    groups = Group.objects.annotate(user_count=Count("user")).prefetch_related("permissions").order_by("name")
    permissions = Permission.objects.select_related("content_type").order_by("content_type__app_label", "codename")
    group_perms_map = {
        str(g.id): {
            "name": g.name,
            "perm_ids": list(g.permissions.values_list("id", flat=True)),
        }
        for g in groups
    }
    return render(
        request,
        "accounts/user_form.html",
        {
            "form": form,
            "action": "Create",
            "groups": groups,
            "permissions": permissions,
            "group_perms_json": json.dumps(group_perms_map),
        },
    )


@admin_required
def role_create(request):
    """Admin creates a new custom System Role."""
    if request.method == "POST":
        form = SystemRoleCreationForm(request.POST)
        if form.is_valid():
            role = form.save()
            msg = f"System Role '{role.name}' created successfully."

            if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.headers.get("accept") == "application/json":
                return JsonResponse({
                    "success": True,
                    "role": {
                        "id": role.id,
                        "name": role.name,
                        "code": role.code,
                        "description": role.description,
                        "is_admin": role.is_admin,
                        "group_id": role.group.id if role.group else None,
                        "group_name": role.group.name if role.group else None,
                        "permission_ids": list(role.group.permissions.values_list("id", flat=True)) if role.group else [],
                    },
                    "message": msg,
                })

            messages.success(request, msg)
            return redirect("accounts:user_list")
        else:
            if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.headers.get("accept") == "application/json":
                errors = {field: [str(e) for e in errs] for field, errs in form.errors.items()}
                return JsonResponse({"success": False, "errors": errors}, status=400)
    else:
        form = SystemRoleCreationForm()

    permissions = Permission.objects.select_related("content_type").order_by("content_type__app_label", "codename")
    return render(request, "accounts/role_form.html", {"form": form, "permissions": permissions})


@admin_required
def user_edit(request, pk):
    """Admin edits an existing user."""
    user_obj = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        form = AdminUserChangeForm(request.POST, request.FILES, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"User '{user_obj.username}' updated successfully.")
            return redirect("accounts:user_list")
    else:
        form = AdminUserChangeForm(instance=user_obj)

    groups = Group.objects.annotate(user_count=Count("user")).prefetch_related("permissions").order_by("name")
    permissions = Permission.objects.select_related("content_type").order_by("content_type__app_label", "codename")
    group_perms_map = {
        str(g.id): {
            "name": g.name,
            "perm_ids": list(g.permissions.values_list("id", flat=True)),
        }
        for g in groups
    }
    return render(
        request,
        "accounts/user_form.html",
        {
            "form": form,
            "action": "Edit",
            "target_user": user_obj,
            "groups": groups,
            "permissions": permissions,
            "group_perms_json": json.dumps(group_perms_map),
        },
    )


@admin_required
def user_toggle_active(request, pk):
    """Admin toggles user active status."""
    user_obj = get_object_or_404(User, pk=pk)

    if user_obj == request.user:
        msg = "You cannot deactivate your own account."
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.headers.get("accept") == "application/json":
            return JsonResponse({"success": False, "error": msg}, status=400)
        messages.error(request, msg)
        return redirect("accounts:user_list")

    user_obj.is_active = not user_obj.is_active
    user_obj.save()
    status_str = "activated" if user_obj.is_active else "deactivated"
    msg = f"User '{user_obj.username}' has been successfully {status_str}."

    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.headers.get("accept") == "application/json":
        return JsonResponse({
            "success": True,
            "is_active": user_obj.is_active,
            "status_display": "Active" if user_obj.is_active else "Inactive",
            "message": msg,
        })

    messages.success(request, msg)
    return redirect("accounts:user_list")


@admin_required
def user_reset_password(request, pk):
    """Admin resets a user's password."""
    user_obj = get_object_or_404(User, pk=pk)

    if user_obj == request.user:
        msg = "You cannot reset your own password here. Please use Account Settings."
        if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.headers.get("accept") == "application/json":
            return JsonResponse({"success": False, "error": msg}, status=400)
        messages.error(request, msg)
        return redirect("accounts:user_list")

    temp_password = request.POST.get("temporary_password", "").strip() if request.method == "POST" else ""
    if not temp_password:
        temp_password = "Aequs@2026!"

    user_obj.set_password(temp_password)
    user_obj.must_change_password = True
    user_obj.save()

    msg = f"Password for '{user_obj.username}' has been reset to '{temp_password}'. The user must change it on next login."

    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.headers.get("accept") == "application/json":
        return JsonResponse({
            "success": True,
            "username": user_obj.username,
            "temp_password": temp_password,
            "message": msg,
        })

    messages.success(request, msg)
    return redirect("accounts:user_list")


@admin_required
def user_detail_api(request, pk):
    """API endpoint returning user detail for modal inspection."""
    user_obj = get_object_or_404(User, pk=pk)

    data = {
        "id": user_obj.pk,
        "username": user_obj.username,
        "full_name": user_obj.get_full_name() or user_obj.username,
        "first_name": user_obj.first_name,
        "last_name": user_obj.last_name,
        "email": user_obj.email or "—",
        "phone": user_obj.phone or "—",
        "role": user_obj.role,
        "role_display": user_obj.get_role_display(),
        "is_active": user_obj.is_active,
        "must_change_password": user_obj.must_change_password,
        "profile_photo_url": user_obj.profile_photo.url if user_obj.profile_photo else None,
        "date_joined": user_obj.date_joined.strftime("%b %d, %Y, %I:%M %p") if user_obj.date_joined else "—",
        "last_login": user_obj.last_login.strftime("%b %d, %Y, %I:%M %p") if user_obj.last_login else "Never logged in",
        "groups": [{"id": g.id, "name": g.name} for g in user_obj.groups.all()],
        "user_permissions": [f"{p.content_type.app_label}.{p.codename}" for p in user_obj.user_permissions.all()],
        "permissions_count": len(user_obj.get_all_permissions()),
    }
    return JsonResponse(data)


@admin_required
def user_export_csv(request):
    """Export filtered user list to CSV file."""
    query = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "").strip()
    status_filter = request.GET.get("status", "").strip()
    group_filter = request.GET.get("group", "").strip()

    users = User.objects.prefetch_related("groups").order_by("-date_joined")

    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )

    if role_filter:
        users = users.filter(role=role_filter)

    if status_filter == "active":
        users = users.filter(is_active=True)
    elif status_filter == "inactive":
        users = users.filter(is_active=False)
    elif status_filter == "pending_pw":
        users = users.filter(must_change_password=True)

    if group_filter:
        if group_filter.isdigit():
            users = users.filter(groups__id=int(group_filter))
        else:
            users = users.filter(groups__name__iexact=group_filter)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="aequs_edutrack_users.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Username",
        "Full Name",
        "Role",
        "Email",
        "Phone",
        "Status",
        "Must Change Password",
        "Groups",
        "Date Joined",
        "Last Login",
    ])

    for u in users:
        group_names = ", ".join([g.name for g in u.groups.all()])
        writer.writerow([
            u.username,
            u.get_full_name() or u.username,
            u.get_role_display(),
            u.email or "",
            u.phone or "",
            "Active" if u.is_active else "Inactive",
            "Yes" if u.must_change_password else "No",
            group_names,
            u.date_joined.strftime("%Y-%m-%d %H:%M") if u.date_joined else "",
            u.last_login.strftime("%Y-%m-%d %H:%M") if u.last_login else "Never",
        ])

    return response
