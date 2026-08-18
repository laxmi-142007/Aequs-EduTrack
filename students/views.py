from django.shortcuts import render, redirect

from .models import Student
from .forms import StudentForm
from academics.models import AcademicRecord


def student_list(request):
    students = Student.objects.all().order_by("-id")

    return render(
        request,
        "students/student_list.html",
        {"students": students},
    )


def add_student(request):
    if request.method == "POST":
        form = StudentForm(request.POST)

        if form.is_valid():
            student = form.save()

            # Automatically create the academic record
            # from the student's current class.
            AcademicRecord.objects.get_or_create(
                student=student,
                academic_year="2026-27",
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
