import os
import io
import csv
import json
import re
from django.conf import settings
from django.db import transaction
from schools.models import School, SchoolResource, GradeStrength

def _get_roster_file_path(program_pk):
    roster_dir = os.path.join(getattr(settings, "MEDIA_ROOT", "media"), "rosters")
    os.makedirs(roster_dir, exist_ok=True)
    return os.path.join(roster_dir, f"program_{program_pk}_roster.json")


def _get_roster_cleared_marker_path(program_pk):
    roster_dir = os.path.join(getattr(settings, "MEDIA_ROOT", "media"), "rosters")
    os.makedirs(roster_dir, exist_ok=True)
    return os.path.join(roster_dir, f"program_{program_pk}_cleared.marker")


def get_program_school_roster(program):
    """
    Returns structured school profile Excel roster data for a given program.
    Dynamically loads either:
    1. Saved/uploaded roster JSON from an uploaded Excel/CSV file for this program.
    2. Dynamically computed from database models (program.participating_schools, GradeStrength, SchoolResource).
    Returns None if no roster has been uploaded and no participating schools exist.
    """
    marker_path = _get_roster_cleared_marker_path(program.pk)
    if os.path.exists(marker_path):
        return None

    # 1. Check for uploaded roster JSON for this program
    saved_path = _get_roster_file_path(program.pk)
    if os.path.exists(saved_path):
        try:
            with open(saved_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Reconnect live school objects
            db_schools = {s.udise_code: s for s in program.participating_schools.all()}
            for item in data.get("schools", []):
                item["school_obj"] = db_schools.get(item.get("udise"))
            return data
        except Exception:
            pass

    # 2. Dynamic roster from participating schools in the database
    part_schools = list(program.participating_schools.all().prefetch_related("grade_strengths", "resources"))
    if not part_schools:
        if program.ngo:
            from trackers.roster import get_ngo_enrollment_roster
            ngo_roster = get_ngo_enrollment_roster(program.ngo, academic_year=program.academic_year)
            if ngo_roster and ngo_roster.get("schools"):
                ngo_roster["program_title"] = program.title
                ngo_roster["donor_title"] = f"Location: {program.location_name or (program.ngo.name if program.ngo else 'Aequs Foundation')}"
                return ngo_roster
        return None

    schools_output = []
    tot_c4 = [0, 0, 0]
    tot_c5 = [0, 0, 0]
    tot_c6 = [0, 0, 0]
    tot_c7 = [0, 0, 0]
    tot_c8 = [0, 0, 0]
    tot_c9 = [0, 0, 0]
    tot_c10 = [0, 0, 0]
    tot_gt = [0, 0, 0]

    for idx, sc in enumerate(part_schools, 1):
        teacher_res = sc.resources.filter(resource_name__icontains="teacher").first()
        teacher_name = teacher_res.resource_name.replace("Science Teacher:", "").strip() if teacher_res else ""
        teacher_mob = teacher_res.details.replace("Mobile:", "").strip() if teacher_res else ""

        grades_by_name = {g.grade_level.upper(): g for g in sc.grade_strengths.all()}
        def _get_g(name_key):
            for k, g in grades_by_name.items():
                if name_key in k:
                    return [g.male_students, g.female_students, g.total_students]
            return [0, 0, 0]

        c4 = _get_g("4")
        c5 = _get_g("5")
        c6 = _get_g("6")
        c7 = _get_g("7")
        c8 = _get_g("8")
        c9 = _get_g("9")
        c10 = _get_g("10")
        all_grades = [c4, c5, c6, c7, c8, c9, c10]
        gt_b = sum(g[0] for g in all_grades)
        gt_g = sum(g[1] for g in all_grades)
        gt_t = sc.student_strength or (gt_b + gt_g)
        gt = [gt_b, gt_g, gt_t]

        for i in range(3):
            tot_c4[i] += c4[i]
            tot_c5[i] += c5[i]
            tot_c6[i] += c6[i]
            tot_c7[i] += c7[i]
            tot_c8[i] += c8[i]
            tot_c9[i] += c9[i]
            tot_c10[i] += c10[i]
            tot_gt[i] += gt[i]

        schools_output.append({
            "sl": idx,
            "name": sc.name,
            "taluk": sc.taluk or sc.district,
            "udise": sc.udise_code,
            "hm": sc.headmaster_name,
            "hm_mob": sc.headmaster_phone,
            "teacher": teacher_name,
            "teacher_mob": teacher_mob,
            "school_obj": sc,
            "rowspan": 1,
            "total_students": gt_t,
            "divisions": [{
                "division": "",
                "c4": c4, "c5": c5, "c6": c6, "c7": c7, "c8": c8, "c9": c9, "c10": c10,
                "gt": gt
            }]
        })

    taluks = sorted(list(set(s["taluk"] for s in schools_output)))
    return {
        "title_org": (program.ngo.name if program.ngo else "AEQUS FOUNDATION"),
        "profile_title": f"School Profile: Academic Year {program.academic_year}",
        "program_title": program.title,
        "donor_title": f"Location: {program.location_name}",
        "academic_year": program.academic_year,
        "schools": schools_output,
        "totals": {
            "c4": tot_c4, "c5": tot_c5, "c6": tot_c6, "c7": tot_c7,
            "c8": tot_c8, "c9": tot_c9, "c10": tot_c10, "gt": tot_gt
        },
        "taluks": taluks,
        "kpis": {
            "total_schools": len(schools_output),
            "total_students": tot_gt[2],
            "total_boys": tot_gt[0],
            "total_girls": tot_gt[1],
            "dlc_students": tot_c6[2],
            "taluks_count": len(taluks),
        }
    }


def parse_and_save_roster(program, uploaded_file):
    """
    Parses an uploaded Excel (.xlsx) or CSV (.csv) file, updates/creates
    School and GradeStrength records, links them to the Program, and saves
    the structured JSON so that the school profile table immediately renders.
    """
    filename = uploaded_file.name.lower()
    raw_rows = []

    # Clear previously dismissed/cleared marker if uploading a new file
    marker_path = _get_roster_cleared_marker_path(program.pk)
    if os.path.exists(marker_path):
        try:
            os.remove(marker_path)
        except Exception:
            pass

    # Read rows from Excel or CSV (Processing ALL sheets in workbook)
    sheets_to_process = []
    if filename.endswith((".xlsx", ".xls")):
        import openpyxl
        wb = openpyxl.load_workbook(uploaded_file, data_only=True)
        for ws in wb.worksheets:
            cur = [list(r) for r in ws.iter_rows(values_only=True) if any(c is not None and str(c).strip() != "" for c in r)]
            if len(cur) >= 2:
                sheets_to_process.append((ws.title, cur))
        wb.close()
    else:
        content_bytes = uploaded_file.read()
        decoded = ""
        for enc in ("utf-8-sig", "utf-8", "cp1252", "iso-8859-1", "utf-16"):
            try:
                decoded = content_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if not decoded:
            raise ValueError("Could not decode CSV file. Please use standard UTF-8 CSV.")
        # Detect delimiter
        sample = decoded[:4096]
        delim = "\t" if sample.count("\t") > sample.count(",") else ","
        reader = csv.reader(io.StringIO(decoded), delimiter=delim)
        raw_rows = [list(r) for r in reader if any(c is not None and str(c).strip() != "" for c in r)]
        sheets_to_process.append(("CSV", raw_rows))

    if not sheets_to_process:
        raise ValueError("Uploaded file contains no readable data.")

    # Find Header Row & Title Info dynamically
    title_org = program.ngo.name if program.ngo else "Partner Organization"
    profile_title = f"School Profile: Academic Year {program.academic_year or '2025-26'}"
    program_title = program.title
    donor_title = f"Location: {program.location_name}" if program.location_name else "Aequs Foundation"

    def _to_int(v):
        if v is None:
            return 0
        s = str(v).replace(",", "").strip()
        try:
            return int(float(s))
        except (ValueError, TypeError):
            return 0

    schools_dict = {}

    for sheet_title, raw_rows in sheets_to_process:
        # Check first rows for titles
        for idx, r in enumerate(raw_rows[:15]):
            row_str = " ".join(str(c or "").lower() for c in r)
            first_cell = str(r[0] or "").strip()
            if any(w in row_str for w in ("foundation", "agastya", "trust", "region", "ngo")):
                if not title_org or title_org == "Partner Organization":
                    title_org = first_cell if first_cell else row_str.strip()
            if "school profile" in row_str or "academic year" in row_str:
                profile_title = first_cell if first_cell else row_str.strip()

        # Find Header Row in this sheet
        header_idx = -1
        for idx, r in enumerate(raw_rows[:15]):
            row_str = " ".join(str(c or "").lower() for c in r)
            if ("name of the school" in row_str) or ("school" in row_str and ("udise" in row_str or "taluk" in row_str or "name" in row_str or "std" in row_str or "sl" in row_str)) or ("hool" in row_str and "taluk" in row_str):
                header_idx = idx
                break

        if header_idx == -1:
            for idx, r in enumerate(raw_rows[:10]):
                if sum(1 for c in r if c and isinstance(c, str) and len(c.strip()) > 1) >= 3:
                    header_idx = idx
                    break

        if header_idx == -1:
            continue

        r0 = [str(c or "").strip() for c in raw_rows[header_idx]]
        col_map = {}
        mobiles = []
        for i, h in enumerate(r0):
            hl = h.lower()
            if "sl" in hl or ("no" in hl and "mobile" not in hl and "hool" not in hl):
                col_map.setdefault("sl", i)
            elif "name of the school" in hl or "name of school" in hl or (("school" in hl or "name" in hl) and "teacher" not in hl and "hm" not in hl):
                col_map.setdefault("name", i)
            elif "taluk" in hl:
                col_map.setdefault("taluk", i)
            elif "udise" in hl or "dise" in hl:
                col_map.setdefault("udise", i)
            elif "hm" in hl or "headmaster" in hl:
                col_map.setdefault("hm", i)
            elif "teacher" in hl:
                col_map.setdefault("teacher", i)
            elif "div" in hl or "sec" in hl:
                col_map.setdefault("div", i)
            if "mobile" in hl or "phone" in hl or "contact" in hl:
                mobiles.append(i)

        if mobiles:
            col_map["hm_mob"] = mobiles[0]
            if len(mobiles) > 1:
                col_map["teacher_mob"] = mobiles[1]

        # Dynamically detect standards in header_row (r0)
        grade_cols = {}
        for i, h in enumerate(r0):
            hl = h.lower()
            for std_num in range(1, 11):
                suffix = '1st' if std_num == 1 else ('2nd' if std_num == 2 else ('3rd' if std_num == 3 else f'{std_num}th'))
                if suffix in hl and any(k in hl for k in ("std", "sdt", "class", "grade")):
                    grade_cols[f"c{std_num}"] = (i, i + 1, i + 2)
                    break
            if "grand total" in hl or ("total" in hl and "total students" in hl):
                grade_cols["gt"] = (i, i + 1, i + 2)

        # Fallback to sequential standard offsets starting at col 9
        if not grade_cols:
            start_grades_idx = 9
            for i, h in enumerate(r0):
                if "4" in h or "class" in h.lower():
                    start_grades_idx = i
                    break
            grade_cols = {
                "c4": (start_grades_idx, start_grades_idx + 1, start_grades_idx + 2),
                "c5": (start_grades_idx + 3, start_grades_idx + 4, start_grades_idx + 5),
                "c6": (start_grades_idx + 6, start_grades_idx + 7, start_grades_idx + 8),
                "c7": (start_grades_idx + 9, start_grades_idx + 10, start_grades_idx + 11),
                "c8": (start_grades_idx + 12, start_grades_idx + 13, start_grades_idx + 14),
                "c9": (start_grades_idx + 15, start_grades_idx + 16, start_grades_idx + 17),
                "c10": (start_grades_idx + 18, start_grades_idx + 19, start_grades_idx + 20),
                "gt": (start_grades_idx + 21, start_grades_idx + 22, start_grades_idx + 23),
            }

        start_r = header_idx + 1
        if start_r < len(raw_rows) and any(str(c or "").strip().upper() in ("B", "G", "T", "BOYS", "GIRLS", "TOTAL") for c in raw_rows[start_r]):
            start_r += 1

        data_rows = raw_rows[start_r:]
        current_school = None

        for r in data_rows:
            row_text = " ".join(str(c or "") for c in r)
            if any(k in row_text for k in ("<USER", "<ADDITIONAL", "my data is in")):
                break

            def _get_val(k):
                idx = col_map.get(k)
                if idx is not None and idx < len(r):
                    val = r[idx]
                    if val is not None:
                        from backend.utils import clean_str_value
                        return clean_str_value(val)
                return ""

            sl = _get_val("sl")
            name = _get_val("name")
            taluk = _get_val("taluk")
            udise = _get_val("udise")
            div = _get_val("div")

            if not name and not sl and not div and ("total" in row_text.lower() or "grand total" in row_text.lower()):
                continue

            if name and name.lower() in ["total", "grand total", "name of the school", "nan", "none", "b", "g", "t"]:
                continue

            # Fallback taluk if missing from row
            if not taluk and sheet_title and not sheet_title.lower().startswith("sheet"):
                clean_st = sheet_title.replace("_", " ").replace("-", " ")
                clean_st = re.sub(r"(school|data|tracker|weekly|junior|yuva)", "", clean_st, flags=re.IGNORECASE).strip()
                if clean_st:
                    taluk = clean_st

            div_obj = {f"c{i}": [0, 0, 0] for i in range(1, 11)}
            div_obj["gt"] = [0, 0, 0]
            for gk, (b_idx, g_idx, t_idx) in grade_cols.items():
                b = _to_int(r[b_idx]) if b_idx < len(r) else 0
                g_v = _to_int(r[g_idx]) if g_idx < len(r) else 0
                t = _to_int(r[t_idx]) if t_idx < len(r) else (b + g_v)
                div_obj[gk] = [b, g_v, t]
            div_obj["division"] = div

            # Compute gt if 0
            if div_obj["gt"][2] == 0:
                tot_b = sum(div_obj[f"c{i}"][0] for i in range(1, 11))
                tot_g = sum(div_obj[f"c{i}"][1] for i in range(1, 11))
                tot_t = sum(div_obj[f"c{i}"][2] for i in range(1, 11))
                div_obj["gt"] = [tot_b, tot_g, tot_t]

            if sl or name:
                if sl and not sl.isdigit() and not name:
                    continue
                clean_name = name.strip().lower() if name else f"school_{len(schools_dict)+1}"
                school_key = clean_name
                if school_key in schools_dict and not sl:
                    existing = schools_dict[school_key]
                    if not existing.get("hm") and _get_val("hm"):
                        existing["hm"] = _get_val("hm")
                        existing["hm_mob"] = _get_val("hm_mob")
                    if not existing.get("teacher") and _get_val("teacher"):
                        existing["teacher"] = _get_val("teacher")
                        existing["teacher_mob"] = _get_val("teacher_mob")
                    if div:
                        existing["divisions"].append(div_obj)
                    else:
                        e_div = existing["divisions"][0]
                        for i in range(1, 11):
                            gk = f"c{i}"
                            if div_obj[gk][2] > 0 and e_div[gk][2] == 0:
                                e_div[gk] = div_obj[gk]
                        e_div["gt"][0] = sum(e_div[f"c{i}"][0] for i in range(1, 11))
                        e_div["gt"][1] = sum(e_div[f"c{i}"][1] for i in range(1, 11))
                        e_div["gt"][2] = sum(e_div[f"c{i}"][2] for i in range(1, 11))
                    current_school = existing
                else:
                    current_school = {
                        "sl": int(sl) if (sl and sl.isdigit()) else (len(schools_dict) + 1),
                        "name": name or f"School {len(schools_dict) + 1}",
                        "taluk": taluk or "Dharwad",
                        "udise": udise or f"29090{len(schools_dict) + 1:06d}",
                        "hm": _get_val("hm"),
                        "hm_mob": _get_val("hm_mob"),
                        "teacher": _get_val("teacher"),
                        "teacher_mob": _get_val("teacher_mob"),
                        "divisions": [div_obj],
                    }
                    schools_dict[school_key] = current_school
            elif div and current_school:
                current_school["divisions"].append(div_obj)

    schools_data = list(schools_dict.values())
    for idx, sc in enumerate(schools_data, start=1):
        sc["sl"] = idx

    if not schools_data:
        raise ValueError("Could not extract school rows from the uploaded file.")

    # Calculate Totals
    calc_totals = {gk: [0, 0, 0] for gk in grade_cols.keys()}
    for sc in schools_data:
        for d in sc["divisions"]:
            for gk in grade_cols.keys():
                for idx in range(3):
                    calc_totals[gk][idx] += d[gk][idx]

    # Save to Database & link to Program
    created_schools = []
    seen_udises = set()
    with transaction.atomic():
        for sc_item in schools_data:
            base_udise = sc_item["udise"]
            cand_udise = base_udise
            cnt = 2
            while cand_udise in seen_udises:
                cand_udise = f"{base_udise}-{cnt}"
                cnt += 1
            seen_udises.add(cand_udise)
            sc_item["udise"] = cand_udise

            tot_strength = sum(d["gt"][2] for d in sc_item["divisions"])
            school_obj, _ = School.objects.update_or_create(
                udise_code=cand_udise,
                defaults={
                    "name": sc_item["name"],
                    "taluk": sc_item["taluk"],
                    "district": "Dharwad",
                    "headmaster_name": sc_item["hm"],
                    "headmaster_phone": sc_item["hm_mob"],
                    "phone": sc_item["hm_mob"],
                    "student_strength": tot_strength,
                    "status": School.Status.ACTIVE,
                }
            )
            sc_item["school_obj_pk"] = school_obj.pk
            created_schools.append(school_obj)

            if sc_item["teacher"]:
                SchoolResource.objects.update_or_create(
                    school=school_obj,
                    resource_name=f"Science Teacher: {sc_item['teacher']}",
                    defaults={
                        "status": "Active",
                        "quantity": 1,
                        "details": f"Mobile: {sc_item['teacher_mob']}" if sc_item["teacher_mob"] else "Science Teacher",
                        "last_updated_note": "Imported from school profile Excel",
                    }
                )

            school_obj.grade_strengths.all().delete()
            grade_labels = [
                ("Class 4th", "c4", 4),
                ("Class 5th", "c5", 5),
                ("Class 6th (DLC)", "c6", 6),
                ("Class 7th", "c7", 7),
                ("Class 8th", "c8", 8),
                ("Class 9th", "c9", 9),
                ("Class 10th", "c10", 10),
            ]
            for g_label, g_key, g_ord in grade_labels:
                m = sum(d[g_key][0] for d in sc_item["divisions"])
                f = sum(d[g_key][1] for d in sc_item["divisions"])
                tot = sum(d[g_key][2] for d in sc_item["divisions"])
                if tot > 0:
                    GradeStrength.objects.create(
                        school=school_obj,
                        grade_level=g_label,
                        male_students=m,
                        female_students=f,
                        total_students=tot,
                        order=g_ord
                    )

            if program.ngo:
                program.ngo.partner_schools.add(school_obj)
            if program.project:
                program.project.target_schools.add(school_obj)

        program.participating_schools.set(created_schools)

    taluks = sorted(list(set(s["taluk"] for s in schools_data)))
    result_data = {
        "title_org": title_org,
        "profile_title": profile_title,
        "program_title": program_title,
        "donor_title": donor_title,
        "academic_year": program.academic_year or "2025-26",
        "schools": schools_data,
        "totals": calc_totals,
        "taluks": taluks,
        "kpis": {
            "total_schools": len(schools_data),
            "total_students": calc_totals["gt"][2],
            "total_boys": calc_totals["gt"][0],
            "total_girls": calc_totals["gt"][1],
            "dlc_students": calc_totals["c6"][2],
            "taluks_count": len(taluks),
        }
    }

    # Save to disk for persistent rendering
    saved_path = _get_roster_file_path(program.pk)
    with open(saved_path, "w", encoding="utf-8") as f:
        # Prepare serializable copy
        serializable_schools = []
        for s in schools_data:
            c = dict(s)
            c.pop("school_obj", None)
            c["rowspan"] = len(s["divisions"])
            c["total_students"] = sum(d["gt"][2] for d in s["divisions"])
            serializable_schools.append(c)
        save_dict = dict(result_data)
        save_dict["schools"] = serializable_schools
        json.dump(save_dict, f, indent=2)

    return result_data
