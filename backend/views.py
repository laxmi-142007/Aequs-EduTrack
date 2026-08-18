from django.shortcuts import render

from schools.models import School
from students.models import Student
from academics.models import AcademicRecord
from eligibility.models import EligibilityRecord
from inventory.models import Laptop, LaptopAssignment
from distributions.models import Distribution


def dashboard(request):
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

        "recent_distributions": Distribution.objects.select_related(
            "student"
        ).order_by("-distribution_date", "-created_at")[:10],
    }

    return render(
        request,
        "dashboard.html",
        context,
    )
