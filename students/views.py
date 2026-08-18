from django.shortcuts import render, redirect
from django.db.models import Q

from .models import Student
from .forms import StudentForm
from schools.models import School
from academics.models import AcademicRecord


def student_list(request):
    queryset = Student.objects.select_related("school").all().order_by("-id")

    # Filter parameters
    search_query = request.GET.get("q", "").strip()
    school_id = request.GET.get("school", "").strip()
    class_filter = request.GET.get("class", "").strip()
    gender_filter = request.GET.get("gender", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if search_query:
        queryset = queryset.filter(
            Q(student_name__icontains=search_query) |
            Q(admission_number__icontains=search_query) |
            Q(roll_number__icontains=search_query)
        )

    if school_id:
        queryset = queryset.filter(school_id=school_id)

    if class_filter:
        queryset = queryset.filter(current_class=class_filter)

    if gender_filter:
        queryset = queryset.filter(gender=gender_filter)

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    distinct_classes = sorted(list(filter(None, Student.objects.values_list("current_class", flat=True).distinct())))
    schools = School.objects.all().order_by("name")

    total_count = Student.objects.count()
    filtered_count = queryset.count()
    active_count = Student.objects.filter(status=Student.Status.ACTIVE).count()

    return render(
        request,
        "students/student_list.html",
        {
            "students": queryset,
            "schools": schools,
            "distinct_classes": distinct_classes,
            "search_query": search_query,
            "selected_school": school_id,
            "selected_class": class_filter,
            "selected_gender": gender_filter,
            "selected_status": status_filter,
            "gender_choices": Student.Gender.choices,
            "status_choices": Student.Status.choices,
            "total_count": total_count,
            "filtered_count": filtered_count,
            "active_count": active_count,
        },
    )


def add_student(request):
    if request.method == "POST":
        form = StudentForm(request.POST)

        if form.is_valid():
            student = form.save()

            # Automatically create academic record from current class
            AcademicRecord.objects.get_or_create(
                student=student,
                academic_year="2025-26",
                class_or_course=student.current_class,
            )

            return redirect("students:list")
    else:
        form = StudentForm()

    return render(
        request,
        "students/add_student.html",
        {"form": form},
    )
