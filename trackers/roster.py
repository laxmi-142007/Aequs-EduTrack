import re
from django.db.models import Q
from programs.models import NGO
from schools.models import School, SchoolResource
from trackers.models import SchoolEnrollment

STD_KEY_MAP = {
    # 1st to 3rd
    "1st std": "c1", "class 1": "c1", "grade 1": "c1", "1": "c1", "std 1": "c1",
    "2nd std": "c2", "class 2": "c2", "grade 2": "c2", "2": "c2", "std 2": "c2",
    "3rd std": "c3", "class 3": "c3", "grade 3": "c3", "3": "c3", "std 3": "c3",
    # 4th to 10th
    "4th std": "c4", "class 4": "c4", "grade 4": "c4", "4": "c4", "std 4": "c4",
    "5th std": "c5", "class 5": "c5", "grade 5": "c5", "5": "c5", "std 5": "c5",
    "6th std": "c6", "class 6": "c6", "grade 6": "c6", "6": "c6", "std 6": "c6",
    "7th std": "c7", "class 7": "c7", "grade 7": "c7", "7": "c7", "std 7": "c7",
    "8th std": "c8", "class 8": "c8", "grade 8": "c8", "8": "c8", "std 8": "c8",
    "9th std": "c9", "class 9": "c9", "grade 9": "c9", "9": "c9", "std 9": "c9",
    "10th std": "c10", "class 10": "c10", "grade 10": "c10", "10": "c10", "std 10": "c10",
}


def normalize_std_key(std_name):
    """Maps varied standard names (e.g. '8th STD', 'Class 8', '8') to canonical class keys ('c8')."""
    clean = str(std_name or "").strip().lower()
    # Check exact/prefix matches
    for k, v in STD_KEY_MAP.items():
        if k in clean:
            return v
    # Regex fallback for pure numbers or ordinal patterns
    m = re.search(r"\b([1-9]|10)(?:st|nd|rd|th)?\b", clean)
    if m:
        return f"c{m.group(1)}"
    return None


def get_ngo_enrollment_roster(ngo, academic_year="2025-26", programme=None, search=None):
    """
    Returns structured school profile Excel roster data for a given NGO module,
    matching the multi-tier header spreadsheet view from the program detail page.

    Aggregates SchoolEnrollment records (or falls back to partner schools with GradeStrength)
    into schools with standard-wise triplets [boys, girls, total] and grand totals.
    """
    ay = (academic_year or "2025-26").strip()
    prog = (programme or "").strip()
    q_str = (search or "").strip()

    # 1. Query SchoolEnrollment scoped strictly to this partner NGO
    enrollment_qs = SchoolEnrollment.objects.filter(ngo=ngo).select_related("school")
    if ay:
        enrollment_qs = enrollment_qs.filter(academic_year=ay)
    if prog:
        enrollment_qs = enrollment_qs.filter(programme=prog)
    if q_str:
        enrollment_qs = enrollment_qs.filter(
            Q(school__name__icontains=q_str)
            | Q(school__taluk__icontains=q_str)
            | Q(school__udise_code__icontains=q_str)
            | Q(school__headmaster_name__icontains=q_str)
            | Q(standard__icontains=q_str)
        )

    schools_dict = {}
    has_enrollment_data = enrollment_qs.exists()

    if has_enrollment_data:
        # Build school-level aggregates from SchoolEnrollment
        for enr in enrollment_qs.order_by("school__name", "standard"):
            sc = enr.school
            if sc.id not in schools_dict:
                teacher_res = sc.resources.filter(resource_name__icontains="teacher").first() if hasattr(sc, "resources") else None
                teacher_name = teacher_res.resource_name.replace("Science Teacher:", "").replace("Teacher:", "").strip() if teacher_res else ""
                teacher_mob = teacher_res.details.replace("Mobile:", "").strip() if teacher_res else ""

                schools_dict[sc.id] = {
                    "id": sc.id,
                    "name": sc.name,
                    "taluk": sc.taluk or sc.district or "Dharwad",
                    "udise": sc.udise_code or "—",
                    "hm": sc.headmaster_name or "",
                    "hm_mob": sc.headmaster_phone or "",
                    "teacher": teacher_name,
                    "teacher_mob": teacher_mob,
                    "school_obj": sc,
                    "grades": {f"c{i}": [0, 0, 0] for i in range(1, 11)},
                    "rowspan": 1,
                    "divisions": [],
                }

            ck = normalize_std_key(enr.standard)
            if ck and ck in schools_dict[sc.id]["grades"]:
                schools_dict[sc.id]["grades"][ck][0] += enr.boys
                schools_dict[sc.id]["grades"][ck][1] += enr.girls
                schools_dict[sc.id]["grades"][ck][2] += enr.total

    else:
        # Fallback: Pivot NGO's partner schools from School & GradeStrength models
        school_qs = ngo.partner_schools.all().order_by("name").prefetch_related("grade_strengths", "resources")
        if q_str:
            school_qs = school_qs.filter(
                Q(name__icontains=q_str)
                | Q(taluk__icontains=q_str)
                | Q(udise_code__icontains=q_str)
                | Q(headmaster_name__icontains=q_str)
            )

        for sc in school_qs:
            teacher_res = sc.resources.filter(resource_name__icontains="teacher").first() if hasattr(sc, "resources") else None
            teacher_name = teacher_res.resource_name.replace("Science Teacher:", "").replace("Teacher:", "").strip() if teacher_res else ""
            teacher_mob = teacher_res.details.replace("Mobile:", "").strip() if teacher_res else ""

            sc_entry = {
                "id": sc.id,
                "name": sc.name,
                "taluk": sc.taluk or sc.district or "Dharwad",
                "udise": sc.udise_code or "—",
                "hm": sc.headmaster_name or "",
                "hm_mob": sc.headmaster_phone or "",
                "teacher": teacher_name,
                "teacher_mob": teacher_mob,
                "school_obj": sc,
                "grades": {f"c{i}": [0, 0, 0] for i in range(1, 11)},
                "rowspan": 1,
                "divisions": [],
            }

            for gs in sc.grade_strengths.all():
                ck = normalize_std_key(gs.grade_level)
                if ck and ck in sc_entry["grades"]:
                    sc_entry["grades"][ck][0] += gs.male_students
                    sc_entry["grades"][ck][1] += gs.female_students
                    sc_entry["grades"][ck][2] += gs.total_students

            schools_dict[sc.id] = sc_entry

    # 2. Finalize schools list, compute grand totals and divisions structure
    schools_output = []
    tot_cols = {f"c{i}": [0, 0, 0] for i in range(1, 11)}
    tot_gt = [0, 0, 0]

    for idx, sc_item in enumerate(schools_dict.values(), 1):
        g = sc_item["grades"]
        for i in range(1, 11):
            key = f"c{i}"
            if g[key][2] == 0 and (g[key][0] + g[key][1] > 0):
                g[key][2] = g[key][0] + g[key][1]

        all_grades = [g[f"c{i}"] for i in range(1, 11)]
        gt_b = sum(x[0] for x in all_grades)
        gt_g = sum(x[1] for x in all_grades)
        gt_t = sum(x[2] for x in all_grades)

        if gt_t == 0 and (gt_b + gt_g > 0):
            gt_t = gt_b + gt_g
        elif gt_t == 0 and sc_item["school_obj"] and sc_item["school_obj"].student_strength:
            gt_t = sc_item["school_obj"].student_strength

        sc_gt = [gt_b, gt_g, gt_t]
        sc_item["sl"] = idx
        sc_item["total_students"] = gt_t
        sc_item["divisions"] = [{
            "division": "",
            "c1": g["c1"], "c2": g["c2"], "c3": g["c3"],
            "c4": g["c4"], "c5": g["c5"], "c6": g["c6"],
            "c7": g["c7"], "c8": g["c8"], "c9": g["c9"],
            "c10": g["c10"],
            "gt": sc_gt,
        }]

        # Accumulate column totals
        for i in range(1, 11):
            key = f"c{i}"
            tot_cols[key][0] += g[key][0]
            tot_cols[key][1] += g[key][1]
            tot_cols[key][2] += g[key][2]

        tot_gt[0] += sc_gt[0]
        tot_gt[1] += sc_gt[1]
        tot_gt[2] += sc_gt[2]

        schools_output.append(sc_item)

    # 3. Detect whether primary grades (1st-3rd) have any headcount
    has_primary = any(
        tot_cols["c1"][2] > 0 or tot_cols["c2"][2] > 0 or tot_cols["c3"][2] > 0
        for _ in [1]
    )

    taluks = sorted(list(set(s["taluk"] for s in schools_output if s["taluk"] and s["taluk"] != "—")))
    if not taluks:
        taluks = ["Dharwad"]

    tot_cols["gt"] = tot_gt
    tot_students = tot_gt[2]
    tot_boys = tot_gt[0]
    tot_girls = tot_gt[1]

    # Gender demographic ratios
    gender_base = (tot_boys + tot_girls) if (tot_boys + tot_girls) > 0 else tot_students
    pct_boys = round((tot_boys / gender_base * 100), 1) if gender_base > 0 else 46.9
    pct_girls = round((tot_girls / gender_base * 100), 1) if gender_base > 0 else 53.1

    prog_title = "All Partner Programmes"
    if prog:
        prog_choices_dict = dict(SchoolEnrollment._meta.get_field("programme").choices)
        prog_title = prog_choices_dict.get(prog, prog)

    return {
        "title_org": ngo.name.upper(),
        "profile_title": f"School Profile: Academic Year {ay}",
        "program_title": prog_title,
        "donor_title": f"Location: {ngo.name} Regional Cluster",
        "academic_year": ay,
        "schools": schools_output,
        "totals": tot_cols,
        "taluks": taluks,
        "has_primary": has_primary,
        "kpis": {
            "total_schools": len(schools_output),
            "total_students": tot_students,
            "total_boys": tot_boys,
            "total_girls": tot_girls,
            "dlc_students": tot_cols["c6"][2],
            "taluks_count": len(taluks),
            "pct_boys": pct_boys,
            "pct_girls": pct_girls,
        },
    }
