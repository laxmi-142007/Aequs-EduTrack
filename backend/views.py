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
        return redirect("dashboard")
    
    error = None
    next_url = request.GET.get("next", "dashboard")
    
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        next_url = request.POST.get("next", "dashboard") or "dashboard"
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
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
