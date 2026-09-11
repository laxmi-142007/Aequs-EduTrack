import csv
import json
import random
import io
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from openpyxl import load_workbook
from .models import School, SchoolMilestone, SchoolResource, GradeStrength
from django.shortcuts import render, redirect
from .models import School
from .forms import SchoolForm
User = get_user_model()
DEFAULT_GRADES = [
    {"grade_level": "Nursery", "male": 120, "female": 135, "change": "+15", "order": 1},
    {"grade_level": "Class 1", "male": 250, "female": 245, "change": "+5", "order": 2},
    {"grade_level": "Class 2", "male": 260, "female": 265, "change": "+10", "order": 3},
    {"grade_level": "Class 3", "male": 240, "female": 230, "change": "-5", "order": 4},
    {"grade_level": "Class 4", "male": 220, "female": 215, "change": "0", "order": 5},
    {"grade_level": "Class 5", "male": 200, "female": 190, "change": "-15", "order": 6},
    {"grade_level": "Class 6 - 12", "male": 350, "female": 320, "change": "+20", "order": 7},
]

def _ensure_default_grades(school):
    actual_students = school.students.all()
    actual_count = actual_students.count()

    if actual_count > 0:
        from django.db.models import Count, Q
        class_counts = actual_students.values("current_class").annotate(
            males=Count("id", filter=Q(gender="MALE")),
            females=Count("id", filter=Q(gender="FEMALE")),
            total=Count("id")
        )
        school.grade_strengths.all().delete()
        for idx, item in enumerate(class_counts, 1):
            c_name_val = item["current_class"]
            c_name = c_name_val or "General"
            class_student_names = list(actual_students.filter(current_class=c_name_val).values_list("student_name", flat=True))
            names_str = ", ".join([n for n in class_student_names if n])
            GradeStrength.objects.create(
                school=school,
                grade_level=c_name,
                male_students=item["males"],
                female_students=item["females"],
                total_students=item["total"],
                change_vs_last_year="0",
                order=idx,
                student_names=names_str,
            )
        if school.student_strength != actual_count:
            school.student_strength = actual_count
            school.save(update_fields=["student_strength"])
    else:
        # No students added to this school yet -> student strength stays at 0
        school.grade_strengths.all().delete()
        if school.student_strength != 0:
            school.student_strength = 0
            school.save(update_fields=["student_strength"])


def _school_to_dict(school):
    actual_count = school.students.count() if hasattr(school, "students") else 0
    ngos = list(school.partner_ngos.values("id", "name", "code")) if hasattr(school, "partner_ngos") else []
    primary_ngo = ngos[0] if ngos else None
    return {
        "id": school.id,
        "name": school.name,
        "udise_code": school.udise_code,
        "address": school.address,
        "district": school.district,
        "taluk": school.taluk,
        "village": school.village,
        "pincode": school.pincode,
        "phone": school.phone,
        "email": school.email,
        "website": school.website,
        "headmaster_name": school.headmaster_name,
        "headmaster_phone": school.headmaster_phone,
        "headmaster_qualification": school.headmaster_qualification,
        "headmaster_experience": school.headmaster_experience,
        "headmaster_photo_url": school.headmaster_photo.url if school.headmaster_photo else "",
        "affiliation": school.affiliation,
        "student_strength": actual_count,
        "established_date": school.established_date.strftime("%Y-%m-%d") if school.established_date else "",
        "established_year": school.established_year or "",
        "status": school.status,
        "ngos": ngos,
        "primary_ngo": primary_ngo,
    }


def school_root_redirect(request):
    """
    Do not maintain a central place for schools.
    Redirect directly to the separate Pratham school module.
    """
    return redirect("schools:portal_pratham")


@ensure_csrf_cookie
def portal_view(request, ngo_slug="pratham"):
    """
    Separate School Management Modules for each partner NGO:
    - Pratham (/schools/pratham/)
    - Agastya (/schools/agastya/)
    - Youth for Seva (/schools/yfs/)
    Keeps each organization's schools completely isolated and separate.
    """
    from programs.models import NGO
    from programs.views import ensure_default_ngos
    ensure_default_ngos()

    # Guarantee all existing schools are assigned to one of the 3 partner NGOs
    all_schools = School.objects.all().order_by("name").prefetch_related("partner_ngos")
    for s in all_schools:
        _ensure_default_grades(s)

    core_ngos = list(NGO.objects.filter(code__in=["PRATHAM", "AGASTYA", "YFS"]).order_by("name"))
    # If any legacy schools are unassigned to any NGO, attach them only to Pratham
    unassigned_schools = [s for s in all_schools if s.partner_ngos.count() == 0]
    if unassigned_schools:
        pratham_ngo = NGO.objects.filter(code="PRATHAM").first()
        if pratham_ngo:
            pratham_ngo.partner_schools.add(*unassigned_schools)

    # Determine requested NGO slug
    requested_slug = (ngo_slug or request.GET.get("ngo", "pratham")).strip().lower()
    if requested_slug in ["all", ""]:
        return redirect("schools:portal_pratham")

    slug_to_code = {
        "pratham": "PRATHAM",
        "agastya": "AGASTYA",
        "yfs": "YFS",
        "youth-for-seva": "YFS",
    }
    target_code = slug_to_code.get(requested_slug, requested_slug.upper())

    current_ngo = NGO.objects.filter(code__iexact=target_code).first()
    if not current_ngo:
        current_ngo = NGO.objects.filter(code="PRATHAM").first()
        target_code = "PRATHAM"
        requested_slug = "pratham"

    # Fetch STRICTLY this NGO's schools (kept completely separate)
    schools = current_ngo.partner_schools.all().order_by("name").prefetch_related("students")
    total_students = sum(s.student_strength for s in schools)
    selected_school = schools.first()

    # Build navigation modules list for quick switching between the separate NGO modules
    ngo_nav = []
    for ngo in core_ngos:
        count = ngo.partner_schools.count()
        ngo_nav.append({
            "id": ngo.id,
            "name": ngo.name,
            "code": ngo.code,
            "code_lower": ngo.code.lower(),
            "url": f"/schools/{ngo.code.lower()}/",
            "school_count": count,
            "is_active": (ngo.code == target_code),
        })

    context = {
        "current_ngo": current_ngo,
        "schools": schools,
        "selected_school": selected_school,
        "total_students": total_students,
        "ngo_nav": ngo_nav,
        "requested_ngo": requested_slug,
        "user_authenticated": request.user.is_authenticated,
        "username": request.user.username if request.user.is_authenticated else "Admin",
    }
    return render(request, "schools/portal.html", context)


def school_list(request):
    """Redirect to separate Pratham school module"""
    return redirect("schools:portal_pratham")


def school_create(request):
    if request.method == "POST":
        form = SchoolForm(request.POST, request.FILES)
        if form.is_valid():
            school = form.save()
            _ensure_default_grades(school)
            return redirect("schools:portal")

    else:
        form = SchoolForm()
    return render(request, "schools/form.html", {"form": form})


# =========================================================================
# JSON / REST API ENDPOINTS
# =========================================================================

def api_schools_list(request):
    """List all schools in JSON format"""
    schools = School.objects.all().order_by("name")
    data = [_school_to_dict(s) for s in schools]
    return JsonResponse({"success": True, "schools": data, "count": len(data)})


def api_school_detail(request, school_id):
    """Get complete details, strength, milestones, and resources for a school"""
    school = get_object_or_404(School, id=school_id)
    _ensure_default_grades(school)
    
    strengths = list(school.grade_strengths.values(
        "id", "grade_level", "student_names", "male_students", "female_students", "total_students", "change_vs_last_year", "order"
    ))
    
    milestones = list(school.milestones.values(
        "id", "title", "year_or_date", "details", "impact", "created_at"
    ))
    for m in milestones:
        m["created_at"] = m["created_at"].strftime("%Y-%m-%d")
        
    resources = list(school.resources.values(
        "id", "resource_name", "status", "quantity", "last_updated_note", "details", "created_at"
    ))
    for r in resources:
        r["created_at"] = r["created_at"].strftime("%Y-%m-%d")
        
    return JsonResponse({
        "success": True,
        "school": _school_to_dict(school),
        "strengths": strengths,
        "milestones": milestones,
        "resources": resources,
    })


@require_http_methods(["POST"])
def api_add_school(request):
    """Add a new school from Tab 1"""
    try:
        # Handle both JSON and form data
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        name = data.get("name") or data.get("schoolName", "").strip()
        location = data.get("location") or data.get("village", "").strip()
        state = data.get("state") or data.get("district", "").strip()
        admission_date = data.get("admissionDate") or data.get("established_date", "")
        udise_code = data.get("udise_code", "").strip()
        affiliation = data.get("affiliation") or "State"
        
        if not name:
            return JsonResponse({"success": False, "error": "School name is required."}, status=400)

        if not udise_code:
            existing_codes = set(School.objects.values_list("udise_code", flat=True))
            while True:
                candidate = f"29{random.randint(100000000, 999999999)}"
                if candidate not in existing_codes:
                    udise_code = candidate
                    break

        parsed_date = None
        if admission_date:
            try:
                import datetime
                if isinstance(admission_date, str):
                    parsed_date = datetime.date.fromisoformat(admission_date.strip())
                else:
                    parsed_date = admission_date
            except Exception:
                parsed_date = None

        school = School.objects.create(
            name=name,
            udise_code=udise_code,
            village=location,
            district=state or "General District",
            address=f"{location}, {state}".strip(", "),
            established_date=parsed_date,
            affiliation=affiliation,
            status=School.Status.ACTIVE,
        )
        
        # Initialize default grades & strength
        _ensure_default_grades(school)

        # Associate with selected NGO partner module (Pratham, Agastya, Youth for Seva)
        ngo_val = data.get("ngo") or data.get("ngo_id") or data.get("ngo_code") or "PRATHAM"
        try:
            from programs.models import NGO
            ngo = NGO.objects.filter(code__iexact=str(ngo_val)).first() or NGO.objects.filter(name__icontains=str(ngo_val)).first() or NGO.objects.filter(id=int(ngo_val) if str(ngo_val).isdigit() else 0).first()
            if not ngo:
                ngo = NGO.objects.filter(code="PRATHAM").first()
            if ngo:
                ngo.partner_schools.add(school)
        except Exception:
            pass

        try:
            from reports.models import log_activity
            log_activity(request, f"Registered new school '{school.name}' (UDISE: {school.udise_code})", category="SCHOOL")
        except Exception:
            pass

        return JsonResponse({
            "success": True,
            "message": f"School '{school.name}' created successfully!",
            "school": _school_to_dict(school),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_clear_all_schools(request):
    """Clear/delete all schools and their associated records from the database"""
    try:
        from students.models import Student
        from eligibility.models import EligibilityRecord
        from distributions.models import Distribution
        from academics.models import AcademicRecord

        with transaction.atomic():
            Distribution.objects.all().delete()
            EligibilityRecord.objects.all().delete()
            AcademicRecord.objects.all().delete()
            Student.objects.all().delete()
            SchoolMilestone.objects.all().delete()
            SchoolResource.objects.all().delete()
            GradeStrength.objects.all().delete()
            deleted_count, _ = School.objects.all().delete()

        try:
            from reports.models import log_activity
            log_activity(request, f"Cleared all schools from database ({deleted_count} schools deleted)", category="SCHOOL")
        except Exception:
            pass

        return JsonResponse({
            "success": True,
            "message": f"Successfully deleted {deleted_count} school(s) and associated data.",
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)}, status=500)



@require_http_methods(["POST"])
def api_clear_all_schools(request):
    """Clear/delete all schools and their associated records from the database"""
    try:
        from students.models import Student
        from eligibility.models import EligibilityRecord
        from distributions.models import Distribution
        from academics.models import AcademicRecord
        from inventory.models import LaptopAssignment
        from internships.models import InternshipPlacement

        with transaction.atomic():
            InternshipPlacement.objects.all().delete()
            LaptopAssignment.objects.all().delete()
            Distribution.objects.all().delete()
            EligibilityRecord.objects.all().delete()
            AcademicRecord.objects.all().delete()
            Student.objects.all().delete()
            SchoolMilestone.objects.all().delete()
            SchoolResource.objects.all().delete()
            GradeStrength.objects.all().delete()
            deleted_count, _ = School.objects.all().delete()

        try:
            from reports.models import log_activity
            log_activity(request, f"Cleared all schools from database ({deleted_count} schools deleted)", category="SCHOOL")
        except Exception:
            pass

        return JsonResponse({
            "success": True,
            "message": f"Successfully deleted {deleted_count} school(s) and associated data.",
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_edit_school(request, school_id):
    """Edit school details from Modal or Tab 2"""
    try:
        school = get_object_or_404(School, id=school_id)
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        name = data.get("name") or data.get("editSchoolName")
        udise_code = data.get("udise_code")
        village = data.get("village") or data.get("location")
        district = data.get("district") or data.get("state")
        address = data.get("address")
        phone = data.get("phone")
        email = data.get("email")
        website = data.get("website")
        principal = data.get("headmaster_name") or data.get("principal") or data.get("editPrincipal")
        headmaster_phone = data.get("headmaster_phone")
        headmaster_qualification = data.get("headmaster_qualification")
        affiliation = data.get("affiliation") or data.get("editAffiliation")
        student_strength = data.get("student_strength")
        status = data.get("status")

        if name:
            school.name = name.strip()
        if udise_code:
            school.udise_code = udise_code.strip()
        if village is not None:
            school.village = village.strip()
        if district is not None:
            school.district = district.strip()
        if address is not None:
            school.address = address.strip()
        if phone is not None:
            school.phone = phone.strip()
        if email is not None:
            school.email = email.strip()
        if website is not None:
            school.website = website.strip()
        if principal is not None:
            school.headmaster_name = principal.strip()
        if headmaster_phone is not None:
            school.headmaster_phone = headmaster_phone.strip()
        if headmaster_qualification is not None:
            school.headmaster_qualification = headmaster_qualification.strip()
        if affiliation:
            school.affiliation = affiliation.strip()
        if status and status in dict(School.Status.choices):
            school.status = status
        if student_strength is not None:
            try:
                school.student_strength = int(student_strength)
            except (ValueError, TypeError):
                pass

        school.save()

        # Update NGO Partner module association if provided
        ngo_val = data.get("ngo") or data.get("ngo_id") or data.get("ngo_code") or data.get("editNgo")
        if ngo_val:
            try:
                from programs.models import NGO
                ngo = NGO.objects.filter(code__iexact=str(ngo_val)).first() or NGO.objects.filter(name__icontains=str(ngo_val)).first() or NGO.objects.filter(id=int(ngo_val) if str(ngo_val).isdigit() else 0).first()
                if ngo:
                    school.partner_ngos.clear()
                    ngo.partner_schools.add(school)
            except Exception:
                pass

        return JsonResponse({
            "success": True,
            "message": f"School '{school.name}' updated successfully!",
            "school": _school_to_dict(school),
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_update_contact(request, school_id):
    """Save contact information from Tab 3"""
    try:
        school = get_object_or_404(School, id=school_id)
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        phone = data.get("phone", "").strip()
        email = data.get("email", "").strip()
        website = data.get("website", "").strip()

        school.phone = phone
        school.email = email
        school.website = website
        school.save(update_fields=["phone", "email", "website", "updated_at"])

        return JsonResponse({
            "success": True,
            "message": "Contact information saved successfully!",
            "school": _school_to_dict(school),
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_update_headmaster(request, school_id):
    """Update Headmaster profile & photo from Tab 4"""
    try:
        school = get_object_or_404(School, id=school_id)
        data = request.POST

        name = data.get("headmasterName", "").strip()
        qualification = data.get("headmasterQualification", "").strip()
        experience = data.get("headmasterExperience")

        if name:
            school.headmaster_name = name
        if qualification:
            school.headmaster_qualification = qualification
        if experience is not None and experience != "":
            try:
                school.headmaster_experience = int(experience)
            except ValueError:
                pass

        if "headmasterPhoto" in request.FILES:
            school.headmaster_photo = request.FILES["headmasterPhoto"]

        school.save()

        return JsonResponse({
            "success": True,
            "message": "Headmaster profile updated successfully!",
            "photo_url": school.headmaster_photo.url if school.headmaster_photo else "",
            "school": _school_to_dict(school),
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def api_get_strength(request, school_id):
    """Get school-wise student strength"""
    school = get_object_or_404(School, id=school_id)
    _ensure_default_grades(school)
    strengths = list(school.grade_strengths.values(
        "id", "grade_level", "student_names", "male_students", "female_students", "total_students", "change_vs_last_year", "order"
    ))
    return JsonResponse({
        "success": True,
        "school_id": school.id,
        "school_name": school.name,
        "total_strength": school.student_strength,
        "strengths": strengths,
    })


@require_http_methods(["POST"])
def api_update_strength(request, school_id):
    """Update a specific grade strength record"""
    try:
        school = get_object_or_404(School, id=school_id)
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        grade_id = data.get("grade_id")
        grade_level = data.get("grade_level")
        male = int(data.get("male_students", 0))
        female = int(data.get("female_students", 0))
        change = data.get("change_vs_last_year", "0")

        student_names = data.get("student_names", "")

        if grade_id:
            grade_obj = get_object_or_404(GradeStrength, id=grade_id, school=school)
            grade_obj.male_students = male
            grade_obj.female_students = female
            grade_obj.total_students = male + female
            grade_obj.change_vs_last_year = change
            if "student_names" in data:
                grade_obj.student_names = student_names
            grade_obj.save()
        elif grade_level:
            grade_obj, _ = GradeStrength.objects.update_or_create(
                school=school,
                grade_level=grade_level,
                defaults={
                    "male_students": male,
                    "female_students": female,
                    "total_students": male + female,
                    "change_vs_last_year": change,
                    "student_names": student_names,
                }
            )

        # Recalculate total strength for the school
        total = sum(g.total_students for g in school.grade_strengths.all())
        school.student_strength = total
        school.save(update_fields=["student_strength", "updated_at"])

        return JsonResponse({
            "success": True,
            "message": "Student strength updated successfully!",
            "total_strength": school.student_strength,
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


def export_student_strength_csv(request, school_id=None):
    """Export student strength table to CSV"""
    response = HttpResponse(content_type="text/csv")
    
    if school_id:
        school = get_object_or_404(School, id=school_id)
        _ensure_default_grades(school)
        filename = f"Student_Strength_{school.name.replace(' ', '_')}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        writer.writerow(["School Name", school.name])
        writer.writerow(["UDISE Code", school.udise_code])
        writer.writerow([])
        writer.writerow(["Grade Level", "Student Names", "Male Students", "Female Students", "Total Students", "Change (vs. Last Year)"])
        
        for g in school.grade_strengths.all():
            writer.writerow([
                g.grade_level,
                g.student_names or "-",
                g.male_students,
                g.female_students,
                g.total_students,
                g.change_vs_last_year,
            ])
            
        total_m = sum(g.male_students for g in school.grade_strengths.all())
        total_f = sum(g.female_students for g in school.grade_strengths.all())
        writer.writerow(["Total", "-", total_m, total_f, school.student_strength, ""])
    else:
        response["Content-Disposition"] = 'attachment; filename="All_Schools_Student_Strength.csv"'
        writer = csv.writer(response)
        writer.writerow(["School Name", "UDISE Code", "Grade Level", "Student Names", "Male Students", "Female Students", "Total Students", "Change"])
        for s in School.objects.all():
            _ensure_default_grades(s)
            for g in s.grade_strengths.all():
                writer.writerow([
                    s.name,
                    s.udise_code,
                    g.grade_level,
                    g.student_names or "-",
                    g.male_students,
                    g.female_students,
                    g.total_students,
                    g.change_vs_last_year,
                ])
                
    return response


@require_http_methods(["POST"])
def api_add_milestone(request, school_id):
    """Add a school milestone / history record from Tab 6"""
    try:
        school = get_object_or_404(School, id=school_id)
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        title = data.get("title", "").strip()
        year_or_date = data.get("year_or_date", "").strip()
        details = data.get("details", "").strip()
        impact = data.get("impact", "").strip()

        if not title:
            return JsonResponse({"success": False, "error": "Milestone title is required."}, status=400)

        milestone = SchoolMilestone.objects.create(
            school=school,
            title=title,
            year_or_date=year_or_date,
            details=details,
            impact=impact,
        )

        return JsonResponse({
            "success": True,
            "message": "Milestone added successfully!",
            "milestone": {
                "id": milestone.id,
                "title": milestone.title,
                "year_or_date": milestone.year_or_date,
                "details": milestone.details,
                "impact": milestone.impact,
            }
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_clear_all_schools(request):
    """Clear/delete all school records and associated student/resource data."""
    try:
        from distributions.models import Distribution
        from inventory.models import LaptopAssignment
        from eligibility.models import EligibilityRecord
        from academics.models import AcademicRecord
        from students.models import Student

        with transaction.atomic():
            LaptopAssignment.objects.all().delete()
            Distribution.objects.all().delete()
            EligibilityRecord.objects.all().delete()
            AcademicRecord.objects.all().delete()
            Student.objects.all().delete()
            SchoolResource.objects.all().delete()
            GradeStrength.objects.all().delete()
            SchoolMilestone.objects.all().delete()
            deleted_count, _ = School.objects.all().delete()

        try:
            from reports.models import log_activity
            log_activity(request, f"Cleared all partner schools ({deleted_count} schools deleted)", category="SCHOOL")
        except Exception:
            pass

        return JsonResponse({
            "success": True,
            "message": f"Successfully deleted {deleted_count} school(s) and all associated data."
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_delete_milestone(request, milestone_id):
    """Delete a school milestone"""
    try:
        milestone = get_object_or_404(SchoolMilestone, id=milestone_id)
        milestone.delete()
        return JsonResponse({"success": True, "message": "Milestone deleted successfully."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_add_resource(request, school_id):
    """Add a resource allocation record from Tab 7, deduct inventory stock, and create Distribution record, deduct inventory stock, and create Distribution record"""
    try:
        from distributions.models import Distribution, BenefitType, RecipientType, SchoolEssentialType
        from inventory.models import InventoryItem, StockTransaction

        school = get_object_or_404(School, id=school_id)
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        item_id = data.get("item_id")
        resource_name = data.get("resource_name", "").strip()
        status = data.get("status", "Active").strip()
        quantity = int(data.get("quantity", 1))
        last_updated_note = data.get("last_updated_note", "").strip()
        details = data.get("details", "").strip()

        inventory_item = None
        if item_id:
            inventory_item = InventoryItem.objects.filter(id=item_id).first()

        if not inventory_item and resource_name:
            inventory_item = InventoryItem.objects.filter(item_name__iexact=resource_name).first()

        if not inventory_item:
            return JsonResponse({"success": False, "error": "Selected item is not listed in Inventory. Please select an inventory item."}, status=400)

        if inventory_item.current_stock < quantity:
            return JsonResponse({
                "success": False,
                "error": f"Insufficient stock for '{inventory_item.item_name}'. Available: {inventory_item.current_stock} {inventory_item.unit}, requested: {quantity}."
            }, status=400)

        issued_by = request.user.username if request.user.is_authenticated else "Admin"

        with transaction.atomic():
            prev_stock = inventory_item.current_stock
            inventory_item.current_stock -= quantity
            inventory_item.save(update_fields=["current_stock", "updated_at"])

            StockTransaction.objects.create(
                item=inventory_item,
                transaction_type=StockTransaction.TransactionType.STOCK_OUT,
                quantity=quantity,
                previous_stock=prev_stock,
                new_stock=inventory_item.current_stock,
                source_destination=f"Govt School: {school.name} (UDISE: {school.udise_code})",
                reference_number=f"DIST-SCH-{school.udise_code}",
                performed_by=issued_by,
                notes=f"Allocated via School Portal: {details}".strip(),
            )

            resource = SchoolResource.objects.create(
                school=school,
                resource_name=inventory_item.item_name,
                status=status,
                quantity=quantity,
                last_updated_note=last_updated_note or f"Stock deducted ({inventory_item.current_stock} remaining)",
                details=details,
            )

            essential_type_map = {
                "BENCHES": SchoolEssentialType.BENCHES,
                "DESKS": SchoolEssentialType.DESKS,
                "CHAIRS": SchoolEssentialType.CHAIRS,
                "WHITE BOARDS": SchoolEssentialType.WHITE_BOARDS,
                "WHITEBOARDS": SchoolEssentialType.WHITE_BOARDS,
                "LIBRARY BOOKS": SchoolEssentialType.LIBRARY_BOOKS,
                "LAB EQUIPMENT": SchoolEssentialType.LAB_EQUIPMENT,
                "LABORATORY EQUIPMENT": SchoolEssentialType.LAB_EQUIPMENT,
                "WATER FILTERS": SchoolEssentialType.WATER_FILTERS,
                "FANS": SchoolEssentialType.FANS,
                "SPORTS KITS": SchoolEssentialType.SPORTS_KITS,
                "PROJECTORS": SchoolEssentialType.PROJECTORS,
            }

            norm_name = inventory_item.item_name.upper()
            matched_essential = essential_type_map.get(norm_name, SchoolEssentialType.OTHER)

            distribution = Distribution.objects.create(
                school=school,
                inventory_item=inventory_item,
                benefit_type=BenefitType.SCHOOL_ESSENTIAL,
                recipient_type=RecipientType.SCHOOL,
                essential_item_type=matched_essential,
                quantity=quantity,
                academic_year="2026-27",
                issued_by=issued_by,
                remarks=f"School Resource Allocation: {inventory_item.item_name}. {details}".strip(),
                distribution_date=timezone.localdate(),
            )

        return JsonResponse({
            "success": True,
            "message": f"Successfully allocated {quantity} {inventory_item.unit} of '{inventory_item.item_name}' to {school.name}. Stock remaining: {inventory_item.current_stock}.",
            "resource": {
                "id": resource.id,
                "resource_name": resource.resource_name,
                "status": resource.status,
                "quantity": resource.quantity,
                "last_updated_note": resource.last_updated_note,
                "details": resource.details,
            },
            "remaining_stock": inventory_item.current_stock,
            "distribution_id": distribution.id,
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_delete_resource(request, resource_id):
    """Delete an allocated resource and associated distribution record"""
    try:
        from distributions.models import Distribution

        resource = get_object_or_404(SchoolResource, id=resource_id)
        school = resource.school
        res_name = resource.resource_name

        # Delete associated distribution record for this school resource
        Distribution.objects.filter(
            school=school,
            remarks__icontains=res_name,
            quantity=resource.quantity
        ).delete()

        resource.delete()
        return JsonResponse({"success": True, "message": "Resource deleted successfully."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_login(request):
    """Admin Login API"""
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if not username or not password:
            return JsonResponse({"success": False, "error": "Username and password are required."}, status=400)

        # Authenticate user with Django auth
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({
                "success": True,
                "message": f"Welcome back, {user.username}!",
                "user": {
                    "username": user.username,
                    "is_authenticated": True,
                }
            })
        else:
            # Check if demo admin login or if a superuser/user exists
            if username == "admin" and password == "admin123":
                admin_user, created = User.objects.get_or_create(
                    username="admin",
                    defaults={"is_staff": True, "is_superuser": True}
                )
                if created:
                    admin_user.set_password("admin123")
                    admin_user.save()
                login(request, admin_user)
                return JsonResponse({
                    "success": True,
                    "message": "Welcome, Administrator!",
                    "user": {"username": "admin", "is_authenticated": True}
                })

            # Check if any user matches username to authenticate or standard admin
            return JsonResponse({"success": False, "error": "Invalid username or password."}, status=401)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["POST"])
def api_logout(request):
    """Logout API"""
    logout(request)
    return JsonResponse({"success": True, "message": "Logged out successfully."})
def bulk_upload_schools(request, ngo_slug=None):
    from programs.models import NGO
    from programs.views import ensure_default_ngos
    ensure_default_ngos()

    target_slug = (
        ngo_slug
        or request.POST.get("ngo")
        or request.GET.get("ngo")
        or "pratham"
    ).strip().lower()

    slug_to_code = {
        "pratham": "PRATHAM",
        "agastya": "AGASTYA",
        "yfs": "YFS",
        "youth-for-seva": "YFS",
    }
    target_code = slug_to_code.get(target_slug, target_slug.upper())
    target_ngo = NGO.objects.filter(code__iexact=target_code).first()
    if not target_ngo:
        target_ngo = NGO.objects.filter(code="PRATHAM").first()
        target_code = "PRATHAM"
        target_slug = "pratham"

    all_ngos = list(NGO.objects.filter(code__in=["PRATHAM", "AGASTYA", "YFS"]).order_by("name"))
    if not all_ngos:
        all_ngos = list(NGO.objects.all().order_by("name"))

    def _redirect_back():
        return redirect("schools:bulk_upload_for_ngo", ngo_slug=target_slug)

    if request.method != "POST":
        return render(
            request,
            "schools/bulk_upload.html",
            {
                "target_ngo": target_ngo,
                "target_slug": target_slug,
                "all_ngos": all_ngos,
            },
        )

    uploaded_file = (
        request.FILES.get("school_file")
        or request.FILES.get("student_file")
        or request.FILES.get("csv_file")
        or request.FILES.get("file")
    )

    if not uploaded_file:
        messages.error(
            request,
            "Please select an Excel (.xlsx) or CSV (.csv) file."
        )
        return _redirect_back()

    filename = uploaded_file.name.lower()

    if not filename.endswith((".xlsx", ".csv")):
        messages.error(
            request,
            "Only Excel (.xlsx) and CSV (.csv) files are supported."
        )
        return _redirect_back()

    try:

        # ------------------------------------------------------------
        # READ EXCEL
        # ------------------------------------------------------------

        if filename.endswith(".xlsx"):

            workbook = load_workbook(
                filename=uploaded_file,
                read_only=True,
                data_only=True,
            )

            worksheet = workbook.active
            if worksheet is None:
                messages.error(request, "The Excel file is empty or has no active sheet.")
                return _redirect_back()

            rows = list(
                worksheet.iter_rows(values_only=True)
            )

            workbook.close()

            if not rows:
                messages.error(
                    request,
                    "The Excel file is empty."
                )
                return _redirect_back()

            headers = [
                str(value).strip().lower()
                if value is not None else ""
                for value in rows[0]
            ]

            data_rows = rows[1:]

        # ------------------------------------------------------------
        # READ CSV
        # ------------------------------------------------------------

        else:

            decoded_file = uploaded_file.read().decode("utf-8-sig")

            csv_file = io.StringIO(decoded_file)

            reader = csv.reader(csv_file)

            rows = list(reader)

            if not rows:
                messages.error(
                    request,
                    "The CSV file is empty."
                )
                return _redirect_back()

            headers = [
                str(value).strip().lower()
                if value is not None else ""
                for value in rows[0]
            ]

            data_rows = rows[1:]

        # ------------------------------------------------------------
        # REQUIRED COLUMNS
        # ------------------------------------------------------------

        required_columns = {
            "name",
            "udise_code",
            "district",
        }

        missing_columns = (
            required_columns - set(headers)
        )

        if missing_columns:

            messages.error(
                request,
                "Missing required columns: "
                + ", ".join(sorted(missing_columns))
            )

            return _redirect_back()

        # ------------------------------------------------------------
        # VALID OPTIONS
        # ------------------------------------------------------------

        valid_affiliations = {
            choice[0]
            for choice in School.AFFILIATION_CHOICES
        }

        valid_statuses = {
            choice[0]
            for choice in School.Status.choices
        }

        prepared_schools = []
        errors = []

        # ------------------------------------------------------------
        # PROCESS ROWS
        # ------------------------------------------------------------

        for row_number, row in enumerate(
            data_rows,
            start=2
        ):

            data = {}

            for index, header in enumerate(headers):

                if not header:
                    continue

                value = (
                    row[index]
                    if index < len(row)
                    else ""
                )

                if value is None:
                    value = ""

                data[header] = value

            name = str(
                data.get("name", "")
            ).strip()

            udise_code = str(
                data.get("udise_code", "")
            ).strip()

            district = str(
                data.get("district", "")
            ).strip()

            if not name:
                errors.append(
                    f"Row {row_number}: name is required."
                )

            if not udise_code:
                errors.append(
                    f"Row {row_number}: udise_code is required."
                )

            if not district:
                errors.append(
                    f"Row {row_number}: district is required."
                )

            if udise_code and School.objects.filter(
                udise_code=udise_code
            ).exists():

                errors.append(
                    f"Row {row_number}: UDISE code "
                    f"'{udise_code}' already exists."
                )

            # --------------------------------------------------------
            # AFFILIATION
            # --------------------------------------------------------

            affiliation = str(
                data.get(
                    "affiliation",
                    "State"
                )
            ).strip()

            if affiliation not in valid_affiliations:

                errors.append(
                    f"Row {row_number}: invalid affiliation "
                    f"'{affiliation}'. Use CBSE, State or ICSE."
                )

            # --------------------------------------------------------
            # STATUS
            # --------------------------------------------------------

            status = str(
                data.get(
                    "status",
                    "ACTIVE"
                )
            ).strip().upper()

            if status not in valid_statuses:

                errors.append(
                    f"Row {row_number}: invalid status "
                    f"'{status}'. Use ACTIVE or INACTIVE."
                )

            # --------------------------------------------------------
            # ESTABLISHED DATE
            # --------------------------------------------------------

            established_date = None

            date_value = data.get(
                "established_date",
                ""
            )

            if date_value:

                if isinstance(date_value, datetime):

                    established_date = date_value.date()

                elif hasattr(date_value, "year") and hasattr(
                    date_value, "month"
                ):

                    established_date = date_value

                else:

                    try:

                        established_date = datetime.strptime(
                            str(date_value).strip(),
                            "%Y-%m-%d"
                        ).date()

                    except ValueError:

                        errors.append(
                            f"Row {row_number}: established_date "
                            "must be YYYY-MM-DD."
                        )

            # --------------------------------------------------------
            # ESTABLISHED YEAR
            # --------------------------------------------------------

            established_year = None

            year_value = data.get(
                "established_year",
                ""
            )

            if year_value != "":

                try:

                    established_year = int(
                        float(year_value)
                    )

                except (
                    ValueError,
                    TypeError
                ):

                    errors.append(
                        f"Row {row_number}: established_year "
                        "must be a number."
                    )

            # --------------------------------------------------------
            # HEADMASTER EXPERIENCE
            # --------------------------------------------------------

            headmaster_experience = None

            experience_value = data.get(
                "headmaster_experience",
                ""
            )

            if experience_value != "":

                try:

                    headmaster_experience = int(
                        float(experience_value)
                    )

                except (
                    ValueError,
                    TypeError
                ):

                    errors.append(
                        f"Row {row_number}: headmaster_experience "
                        "must be a number."
                    )

            # --------------------------------------------------------
            # STUDENT STRENGTH
            # --------------------------------------------------------

            student_strength = 0

            strength_value = data.get(
                "student_strength",
                0
            )

            if strength_value not in ("", None):

                try:

                    student_strength = int(
                        float(strength_value)
                    )

                except (
                    ValueError,
                    TypeError
                ):

                    errors.append(
                        f"Row {row_number}: student_strength "
                        "must be a number."
                    )

            # --------------------------------------------------------
            # PREPARE SCHOOL
            # --------------------------------------------------------

            prepared_schools.append(
                {
                    "name": name,
                    "udise_code": udise_code,

                    "address": str(
                        data.get("address", "")
                    ).strip(),

                    "district": district,

                    "taluk": str(
                        data.get("taluk", "")
                    ).strip(),

                    "village": str(
                        data.get("village", "")
                    ).strip(),

                    "pincode": str(
                        data.get("pincode", "")
                    ).strip(),

                    "phone": str(
                        data.get("phone", "")
                    ).strip(),

                    "email": str(
                        data.get("email", "")
                    ).strip(),

                    "website": str(
                        data.get("website", "")
                    ).strip(),

                    "headmaster_name": str(
                        data.get("headmaster_name", "")
                    ).strip(),

                    "headmaster_phone": str(
                        data.get("headmaster_phone", "")
                    ).strip(),

                    "headmaster_qualification": str(
                        data.get("headmaster_qualification", "")
                    ).strip(),

                    "headmaster_experience":
                        headmaster_experience,

                    "affiliation":
                        affiliation,

                    "student_strength":
                        student_strength,

                    "established_date":
                        established_date,

                    "established_year":
                        established_year,

                    "status":
                        status,
                }
            )

        # ------------------------------------------------------------
        # VALIDATION ERRORS
        # ------------------------------------------------------------

        if errors:
            return render(
                request,
                "schools/bulk_upload.html",
                {
                    "errors": errors,
                    "upload_failed": True,
                    "target_ngo": target_ngo,
                    "target_slug": target_slug,
                    "all_ngos": all_ngos,
                },
            )

        # ------------------------------------------------------------
        # CREATE SCHOOLS
        # ------------------------------------------------------------

        created_count = 0

        with transaction.atomic():

            for school_data in prepared_schools:

                school = School.objects.create(
                    **school_data
                )

                _ensure_default_grades(school)
                target_ngo.partner_schools.add(school)

                created_count += 1

        messages.success(
            request,
            f"Successfully uploaded {created_count} school(s) strictly to {target_ngo.name}."
        )

        return redirect(f"/schools/{target_slug}/")

    except UnicodeDecodeError:

        messages.error(
            request,
            "Could not read the CSV file. "
            "Please save it as UTF-8 CSV."
        )

        return _redirect_back()

    except Exception as exc:

        messages.error(
            request,
            f"School upload failed: {exc}"
        )

        return _redirect_back()
