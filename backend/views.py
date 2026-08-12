from django.shortcuts import render

from schools.models import School
from students.models import Student
from academics.models import AcademicRecord
from eligibility.models import EligibilityRecord
from inventory.models import Laptop, LaptopAssignment


def dashboard(request):
    context = {
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

        "recent_eligibility": EligibilityRecord.objects.select_related(
            "student"
        ).order_by("-checked_at")[:10],

        "recent_assignments": LaptopAssignment.objects.select_related(
            "student",
            "laptop",
        ).order_by("-created_at")[:10],
    }

    return render(request, "dashboard.html", context)