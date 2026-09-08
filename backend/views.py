from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout

from schools.models import School
from students.models import Student
from academics.models import AcademicRecord
from eligibility.models import EligibilityRecord
from inventory.models import Laptop, LaptopAssignment
from internships.models import InternshipPlacement, InternshipProgram
from distributions.models import Distribution


def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard_redirect")

    error = None
    next_url = request.GET.get("next", "accounts:dashboard_redirect")

    if request.method == "POST":
        login_input = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        next_url = request.POST.get("next", "accounts:dashboard_redirect") or "accounts:dashboard_redirect"

        from accounts.models import User

        # 1. Standard authentication attempt
        user = authenticate(request, username=login_input, password=password)

        # 2. Case-insensitive username or email matching
        if user is None and login_input:
            try:
                matched_user = User.objects.filter(username__iexact=login_input).first()
                if not matched_user and "@" in login_input:
                    matched_user = User.objects.filter(email__iexact=login_input).first()
                if matched_user:
                    user = authenticate(request, username=matched_user.username, password=password)
            except Exception:
                user = None

        # 3. Demo admin fallback: ensures admin/admin123 works reliably on any cloned laptop or fresh DB
        if user is None and login_input.lower() == "admin" and password == "admin123":
            try:
                admin_user, created = User.objects.get_or_create(
                    username="admin",
                    defaults={
                        "is_staff": True,
                        "is_superuser": True,
                        "role": "SUPER_ADMIN",
                        "email": "admin@aequsedutrack.org",
                        "must_change_password": False,
                    }
                )
                admin_user.set_password("admin123")
                admin_user.is_active = True
                admin_user.is_staff = True
                admin_user.is_superuser = True
                admin_user.role = "SUPER_ADMIN"
                admin_user.must_change_password = False
                admin_user.save()
                user = authenticate(request, username="admin", password="admin123")
            except Exception:
                pass

        if user is not None:
            if not user.is_active:
                error = "This account has been deactivated. Please contact your administrator."
            else:
                login(request, user)
                return redirect(next_url)
        else:
            error = "Invalid username or password. Please check your credentials."

    return render(request, "login.html", {"error": error, "next": next_url})


def logout_view(request):
    logout(request)
    return redirect("login")


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect("login")
    context = {
        # =========================
        # BASIC COUNTS
        # =========================

        "school_count": School.objects.filter(
            status=School.Status.ACTIVE
        ).count(),

        "student_count": Student.objects.count(),

        "active_student_count": Student.objects.filter(
            status=Student.Status.ACTIVE
        ).count(),

        "academic_record_count": AcademicRecord.objects.count(),

        # =========================
        # ELIGIBILITY
        # =========================

        "eligible_student_count": EligibilityRecord.objects.filter(
            eligible=True
        ).values("student").distinct().count(),

        "eligible_record_count": EligibilityRecord.objects.filter(
            eligible=True
        ).count(),

        "internship_eligible_count": EligibilityRecord.objects.filter(
            benefit_type="INTERNSHIP",
            eligible=True
        ).count(),

        # =========================
        # LAPTOPS
        # =========================

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
        # =========================
        # DISTRIBUTIONS
        # =========================

        "distribution_count": Distribution.objects.count(),

        "students_benefited_count": Distribution.objects.values(
            "student"
        ).distinct().count(),

        # =========================
        # RECENT RECORDS
        # =========================

        "recent_eligibility": EligibilityRecord.objects.select_related(
            "student"
        ).order_by("-checked_at")[:10],

        "recent_assignments": LaptopAssignment.objects.select_related(
            "student",
            "laptop",
        ).order_by("-created_at")[:10],

        "recent_internships": InternshipPlacement.objects.select_related(
            "student",
            "program",
        ).order_by("-created_at")[:10],
        "recent_distributions": Distribution.objects.select_related(
            "student"
        ).order_by("-distribution_date", "-created_at")[:10],
    }

    return render(
        request,
        "dashboard.html",
        context,
    )
