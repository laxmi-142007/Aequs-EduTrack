import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os

def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_table_borders(table, color="CBD5E1", sz="4"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'<w:insideH w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def format_row(row, bg_color=None, is_header=False, font_size=9.5):
    for cell in row.cells:
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        set_cell_margins(cell, top=90, bottom=90, left=130, right=130)
        if bg_color:
            set_cell_background(cell, bg_color)
        for p in cell.paragraphs:
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            for r in p.runs:
                r.font.name = "Segoe UI"
                r.font.size = Pt(font_size)
                if is_header:
                    r.font.bold = True
                    r.font.color.rgb = RGBColor(255, 255, 255)
                else:
                    r.font.color.rgb = RGBColor(15, 23, 42)

def add_styled_heading(doc, text, level):
    h = doc.add_heading(text, level=level)
    h.paragraph_format.keep_with_next = True
    if level == 1:
        h.paragraph_format.space_before = Pt(18)
        h.paragraph_format.space_after = Pt(8)
        for r in h.runs:
            r.font.name = "Segoe UI"
            r.font.size = Pt(20)
            r.font.bold = True
            r.font.color.rgb = RGBColor(15, 23, 42)
    elif level == 2:
        h.paragraph_format.space_before = Pt(16)
        h.paragraph_format.space_after = Pt(6)
        for r in h.runs:
            r.font.name = "Segoe UI"
            r.font.size = Pt(15)
            r.font.bold = True
            r.font.color.rgb = RGBColor(30, 58, 138)
    elif level == 3:
        h.paragraph_format.space_before = Pt(13)
        h.paragraph_format.space_after = Pt(4)
        for r in h.runs:
            r.font.name = "Segoe UI"
            r.font.size = Pt(12)
            r.font.bold = True
            r.font.color.rgb = RGBColor(37, 99, 235)
    return h

def build_timeline_document():
    doc = docx.Document()

    # Page Margins (1 inch A4)
    sec = doc.sections[0]
    sec.top_margin = Inches(1.0)
    sec.bottom_margin = Inches(1.0)
    sec.left_margin = Inches(1.0)
    sec.right_margin = Inches(1.0)
    sec.page_width = Inches(8.27)
    sec.page_height = Inches(11.69)

    # Document Header / Title
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(2)
    run_t = title_p.add_run("Aequs EduTrack — Project Timeline")
    run_t.font.name = "Segoe UI"
    run_t.font.size = Pt(24)
    run_t.font.bold = True
    run_t.font.color.rgb = RGBColor(15, 23, 42)

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_before = Pt(0)
    sub_p.paragraph_format.space_after = Pt(14)
    run_s = sub_p.add_run("Comprehensive Development History, Milestone Tracker & Architectural Evolution")
    run_s.font.name = "Segoe UI"
    run_s.font.size = Pt(11)
    run_s.font.color.rgb = RGBColor(71, 85, 105)

    # Executive Summary Table
    summary_data = [
        ("Project", "Aequs EduTrack — Educational CSR & Logistics Management Platform"),
        ("Sponsor & Initiative", "Aequs Foundation / Corporate Social Responsibility (Belagavi Hub)"),
        ("Development Window", "August 12, 2026 – September 07, 2026"),
        ("Timeline Span", "27 Calendar Days (14 Active Development Days)"),
        ("Total Commits", "61 Commits (+ Architectural Audit & Codebase Streamlining)"),
        ("Core Engineering Team", "2 Primary Contributors (Rishab / Code-Cool-2006, Saloni Dalvi)"),
        ("Current Codebase State", "78/78 Automated Tests Passing (OK), 0 Django System Check Issues"),
        ("Production Blueprint", "Docker / Render Cloud (PostgreSQL) + Local SQLite / Enterprise MSSQL"),
    ]

    t_meta = doc.add_table(rows=len(summary_data), cols=2)
    t_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_meta, color="E2E8F0", sz="6")
    for idx, (lbl, val) in enumerate(summary_data):
        row = t_meta.rows[idx]
        row.cells[0].width = Inches(2.2)
        row.cells[1].width = Inches(4.07)
        row.cells[0].paragraphs[0].add_run(lbl).bold = True
        row.cells[1].paragraphs[0].add_run(val)
        bg = "F8FAFC" if idx % 2 == 0 else "FFFFFF"
        format_row(row, bg_color=bg, is_header=False, font_size=9)
    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Section 1: Gantt Chart
    add_styled_heading(doc, "Development Gantt Chart", level=2)
    p_gantt = doc.add_paragraph("The Gantt chart below illustrates the end-to-end multi-week engineering timeline across 10 sequential and overlapping project phases from initial scaffolding to final optimization:")
    p_gantt.paragraph_format.space_after = Pt(8)

    gantt_img = "docs/images/gantt_chart.png"
    if os.path.exists(gantt_img):
        doc.add_picture(gantt_img, width=Inches(6.27))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.paragraphs[-1].paragraph_format.space_after = Pt(14)

    # Section 2: Day-by-Day Development Log
    add_styled_heading(doc, "Day-by-Day Development Log", level=2)
    doc.add_paragraph("Complete chronological record of all engineering deliverables, architecture milestones, and commits recorded in the repository:").paragraph_format.space_after = Pt(6)

    days_data = [
        {
            "day": "Day 1 — August 12, 2026 (Tuesday)",
            "phase": "Project Foundation & Core Architecture",
            "commits": [
                ("11:03 AM", "Saloni Dalvi", "Initial Aequs EduTrack project creation — Django project scaffolding with core module configuration."),
                ("3:43 PM", "Saloni Dalvi", "Distributions module implementation — Distribution forms, models, templates, and URL routing."),
            ],
            "deliverables": [
                "Django project initialized with custom User model and 5 RBAC roles (Super Admin, Admin, Accountant, Volunteer, Event Coordinator).",
                "School model created with UDISE codes, headmaster contact details, and district/taluk/village geographical hierarchy.",
                "Student model established with admission numbers, parent/guardian information, and enrollment status tracking.",
                "AcademicRecord model linked to students with subject marks, percentage calculation, and promotion tracking.",
                "EligibilityRecord model defining 5 core benefit types (Books, Workbooks, Study Kit, Laptop, Internship).",
                "Asset management models: Laptop and LaptopAssignment tracking hardware serials and student handovers.",
                "Initial web UI: Dashboard KPI summary cards, Student roster & forms, School directory, and Distribution loggers.",
            ]
        },
        {
            "day": "Day 2 — August 13, 2026 (Wednesday)",
            "phase": "REST APIs & Management Services",
            "commits": [
                ("12:18 PM", "Rishab", "Implement modular REST APIs, management commands, and inventory/academic portals for EduTrack system enhancement."),
            ],
            "deliverables": [
                "InventoryItem and StockTransaction models implemented for general warehouse stock management.",
                "Full interactive Inventory Portal template with stock-in, stock-out, and low-inventory threshold alerts.",
                "Full Academics Portal template with grade standings and ranking displays.",
                "School model extended with affiliation details and established_date.",
                "Automated CLI management commands: seed_schools, seed_inventory, and seed_academics.",
                "Distribution services layer with dedicated Study Kit support (StudyKit, StudyKitItem).",
            ]
        },
        {
            "day": "Day 3 — August 18, 2026 (Monday)",
            "phase": "Major Feature Sprint, UI/UX Overhaul & Production Deployment (19 commits)",
            "commits": [
                ("09:26 AM", "Rishab", "Implement internship module including core service logic, dashboard portal templates, and student eligibility management."),
                ("09:45 AM", "Saloni Dalvi", "Implement core EduTrack features (Events, Volunteers, Reports, academic forms, eligibility views)."),
                ("09:56 AM", "Saloni Dalvi", "Git housekeeping — establish .gitignore for temporary and backup files."),
                ("10:49 AM", "Rishab", "Resolve merge conflicts keeping both branches' content in unified codebase."),
                ("10:53 AM", "Rishab", "Fix duplicate HTML tags from merge conflict resolution across portal templates."),
                ("10:54 AM", "Rishab", "Add database migration merge files for distributions and inventory schema alignment."),
                ("11:02 AM", "Rishab", "Fix navigation links for Events, Volunteers, and Reports across all portal sidebars."),
                ("11:27 AM", "Rishab", "Implement modern sleek dark sidebar with Lucide icons across dashboard and eligibility views."),
                ("11:46 AM", "Rishab", "Integrate unified modern dark Lucide sidebar across all application pages."),
                ("11:55 AM", "Rishab", "Unify global CSS design system across all tabs (topbar, tables, buttons, cards)."),
                ("11:58 AM", "Rishab", "Standardize compact density and sizing across Programs & Benefits, Students, and Academics."),
                ("12:01 PM", "Rishab", "Remove inflated Google Outfit fonts and strictly lock compact dashboard scale on Students, Academics, and Programs."),
                ("12:07 PM", "Rishab", "Lock fixed 256px sidebar dimensions and eliminate obsolete conflicting sidebar padding/styles."),
                ("12:21 PM", "Rishab", "Transform sidebar to light theme with white background, clean slate typography, and royal blue accents."),
                ("12:25 PM", "Rishab", "Upgrade dashboard stat cards and tables to modern shadcn UI component aesthetics with Lucide icons."),
                ("12:32 PM", "Rishab", "Wipe and repopulate database with clean, coherent entries adhering strictly to all CSR benefit criteria."),
                ("12:35 PM", "Rishab", "Add responsive multi-attribute filter bar for students by search query, school, class, gender, and status."),
                ("12:47 PM", "Rishab", "Configure production deployment with Gunicorn, Whitenoise, PostgreSQL database support, and Docker/Render blueprints."),
                ("01:58 PM", "Saloni Dalvi", "Restore local distribution and eligibility changes post-merge."),
            ],
            "deliverables": [
                "Internship Program, Placement, and Milestone tracking models with candidate eligibility screening.",
                "Event Management and Volunteer foundational scaffolding linked to CSR community initiatives.",
                "Three iterations of sidebar design culminating in high-contrast royal blue and crisp white styling.",
                "Complete design system: unified table aesthetics, badges, buttons, and modern shadcn card layouts.",
                "Comprehensive Belagavi district realistic mock data seeding script.",
                "Production cloud readiness: Gunicorn WSGI, Whitenoise static bundling, Dockerfile, and render.yaml.",
            ]
        },
        {
            "day": "Day 4 — August 24, 2026 (Sunday)",
            "phase": "Authentication System & Bulk Operations",
            "commits": [
                ("09:16 AM", "Saloni Dalvi", "Update project with bulk upload systems for students, schools, academics, and inventory."),
                ("11:04 AM", "Rishab", "Implement authentication system and apply global branding updates to UI components."),
                ("11:32 AM", "Saloni Dalvi", "Update distribution student selection and eligibility handling."),
            ],
            "deliverables": [
                "Full authentication flow: login, logout, session persistence, and is_authenticated page guards.",
                "Aequs SEZ branded login interface featuring glassmorphic cards and responsive mobile scaling.",
                "Bulk CSV upload workflows with automated column parsing and validation across 4 modules.",
                "Enhanced student selection logic filtering benefit recipients by exact academic requirements.",
            ]
        },
        {
            "day": "Day 5 — August 25, 2026 (Monday)",
            "phase": "Academic Enhancements & Enterprise SQL Server Setup",
            "commits": [
                ("02:16 PM", "Saloni Dalvi", "Add dynamic academic class filter with CourseMaster integration."),
                ("02:29 PM", "Saloni Dalvi", "Configure Microsoft SQL Server database backend for enterprise deployment."),
                ("02:39 PM", "Saloni Dalvi", "Add academic migrations and academic form template refinements."),
            ],
            "deliverables": [
                "Dynamic CourseMaster model allowing administrators to define custom courses, streams, and grades.",
                "Enterprise SQL Server backend integration via mssql-django and pyodbc (supporting localhost\\SQLEXPRESS).",
                "Refined academic record forms with automated percentage and grade point calculation.",
            ]
        },
        {
            "day": "Day 6 — August 26, 2026 (Tuesday)",
            "phase": "Internship Portal Completion",
            "commits": [
                ("02:18 PM", "Saloni Dalvi", "Complete internship management portal with end-to-end lifecycle tracking."),
            ],
            "deliverables": [
                "Full operational Internship Portal: company partner management, student placement tracking, and milestones.",
                "Stipend tracking, mentor assignments, and completion certificate logging for student interns.",
            ]
        },
        {
            "day": "Day 7 — August 27, 2026 (Wednesday)",
            "phase": "School & Academic Module Refinements",
            "commits": [
                ("09:26 AM", "Rishab", "Temporary save and cleanup of school and academic modules."),
                ("11:08 AM", "Rishab", "Implement core school and academic management modules with associated templates and views."),
            ],
            "deliverables": [
                "Refined school administration views and enhanced data synchronization between schools and academics.",
            ]
        },
        {
            "day": "Day 8 — August 28, 2026 (Thursday)",
            "phase": "School Management Portal & Comprehensive API Test Suite (6 commits)",
            "commits": [
                ("04:10 AM", "Rishab", "Implement school management portal views and comprehensive API testing suite."),
                ("04:50 AM", "Rishab", "Implement school portal interface and supporting view and test modules."),
                ("05:36 AM", "Rishab", "Merge remote-tracking branch 'origin/main' into main."),
                ("05:38 AM", "Rishab", "Implement school portal management views and associated API test suite."),
                ("05:58 AM", "Rishab", "Implement school management portal views and API endpoints for CRUD operations and data synchronization."),
                ("10:35 AM", "Saloni Dalvi", "Describe changes and update school management configurations."),
            ],
            "deliverables": [
                "Complete School Management Portal with interactive KPIs (active schools, total students, labs, libraries).",
                "GradeStrength matrix tracking student headcount per grade from Class 1 through Class 10.",
                "Comprehensive automated API test suite covering 78 test cases across schools, students, and inventory.",
            ]
        },
        {
            "day": "Day 9 — August 31, 2026 (Sunday)",
            "phase": "Documentation, Eligibility Engine & Course Resolvers (5 commits)",
            "commits": [
                ("01:00 PM", "Rishab", "User Manual and Project Timeline documentation upload."),
                ("01:00 PM", "Rishab", "Merge branch 'Rishab' into working branch."),
                ("05:17 PM", "Saloni Dalvi", "Fix eligibility bug: BE/Diploma/ITI/PUC courses misread as school classes; add cleanup command."),
                ("05:26 PM", "Saloni Dalvi", "Fix eligibility class display and add class equivalents (10/10th, PU/PUC) to student filter."),
                ("05:35 PM", "Saloni Dalvi", "Resolve merge conflict in students views."),
            ],
            "deliverables": [
                "System User Manual and initial Project Timeline Word documents created and committed.",
                "Critical eligibility engine patch: resolved course classification bug separating higher education (BE, Diploma, ITI, PUC) from K-10 school grades.",
                "Robust class resolver matching equivalent terms ('10th' == 'Class 10', 'PUC' == '12th') across student records.",
            ]
        },
        {
            "day": "Day 10 — September 01, 2026 (Tuesday)",
            "phase": "Inventory Resource Requests & Multi-DB Configuration",
            "commits": [
                ("05:19 PM", "Rishab", "Add inventory resource requests to event creation with multi-database support configuration."),
            ],
            "deliverables": [
                "Integrated Event Resource Requests enabling event managers to reserve warehouse equipment and study kits.",
                "Multi-database fallback configuration supporting local SQLite, Azure/Enterprise MSSQL, and Cloud PostgreSQL.",
            ]
        },
        {
            "day": "Day 11 — September 02, 2026 (Wednesday)",
            "phase": "Inventory Bulk Upload Repair & Stock Tracking UI (4 commits)",
            "commits": [
                ("03:45 PM", "Saloni Dalvi", "Fix inventory bulk upload page form handling and file reading."),
                ("04:19 PM", "Rishab", "Add item status and stock tracking to inventory schema and UI, and remove legacy seed script."),
                ("04:27 PM", "Rishab", "Merge branch 'main' into Rishab branch."),
                ("04:27 PM", "Rishab", "Merge pull request #1 from laxmi-142007/Rishab - Inventory Bulk Upload Fixed."),
            ],
            "deliverables": [
                "Fixed inventory CSV bulk upload pipeline ensuring atomic transactions and instant error reporting on invalid rows.",
                "Live item status tags (In Stock, Low Stock, Depleted) and detailed stock movement ledger.",
                "Pull Request #1 successfully approved and merged.",
            ]
        },
        {
            "day": "Day 12 — September 04, 2026 (Friday)",
            "phase": "Reporting API & Distribution Services Update",
            "commits": [
                ("10:10 AM", "Rishab", "Import JsonResponse to enable JSON-based report responses and live API polling."),
                ("10:49 AM", "Saloni Dalvi", "Update distribution logistics and eligibility services layer."),
            ],
            "deliverables": [
                "Real-time JSON endpoint for activity audit logs (`/reports/api/logs/`) supporting asynchronous dashboard updates.",
                "Refined distribution verification workflows ensuring study kits and laptops are only issued to verified recipients.",
            ]
        },
        {
            "day": "Day 13 — September 05, 2026 (Saturday)",
            "phase": "Volunteer Management System, Public Registration & QR Sharing (12 commits)",
            "commits": [
                ("02:02 PM", "Saloni Dalvi", "Add documents button to intern cards."),
                ("02:05 PM", "Saloni Dalvi", "Update internship, events, inventory and reports features."),
                ("02:43 PM", "Rishab", "Save local feature changes before merge with origin/main."),
                ("02:52 PM", "Rishab", "Merge branch 'origin/main': integrate remote updates with local events, reports, and volunteer features."),
                ("03:03 PM", "Rishab", "Apply merge migrations, dependency updates, and URL compatibility for origin/main."),
                ("03:29 PM", "Rishab", "Top origin/main code over events and reports templates, views, and urls."),
                ("03:53 PM", "Rishab", "Unify origin/main updates with local event, volunteer, and report features."),
                ("04:39 PM", "Rishab", "Add navigation sidebar to internship documents view."),
                ("05:09 PM", "Rishab", "Add Volunteer Form button to volunteer list topbar."),
                ("05:18 PM", "Rishab", "Configure Volunteer Registration routing and topbar buttons."),
                ("05:30 PM", "Rishab", "Add volunteer registration link modal, QR code, and public registration form."),
                ("05:39 PM", "Rishab", "Implement volunteer management system with CRUD operations, reporting, and public registration link sharing."),
            ],
            "deliverables": [
                "Complete Volunteer Management System: volunteer directory, hours contributed, event assignments, and impact tracking.",
                "Dynamic VolunteerFormLink token generation enabling public community volunteer recruitment drives.",
                "Live QR Code generator producing scannable PNG QR codes with high-density error correction.",
                "Public, responsive registration portal allowing community members to register without requiring admin accounts.",
                "Comprehensive audit logging integrating volunteer signups directly into the central compliance log.",
            ]
        },
        {
            "day": "Day 14 — September 07, 2026 (Monday)",
            "phase": "Architectural Audit, Codebase Streamlining & Quality Verification",
            "commits": [
                ("10:15 AM", "Rishab", "Codebase audit: eliminated 52 legacy backup and dump files (-29,811 lines), removed 5 skeleton apps, and unified QR generators."),
            ],
            "deliverables": [
                "Removed 17 dead backup and text dump files (project_frontend.txt, *_backup.py, *.corrupt-backup) totaling ~24,700 lines.",
                "Cleaned 5 empty placeholder apps (audit, documents, notifications, donations, expense_management) from tree and INSTALLED_APPS.",
                "Unified duplicate QR generator views in volunteers/views.py into a single high-performance handler.",
                "Cleaned requirements.txt removing redundant transitive dependencies (asgiref, sqlparse).",
                "Full verification: 78/78 tests passed cleanly (Ran in 5.6s), and Django system check reported zero issues.",
            ]
        },
    ]

    for d_info in days_data:
        add_styled_heading(doc, f"📅 {d_info['day']}", level=3)
        p_phase = doc.add_paragraph()
        r_p1 = p_phase.add_run("Phase: ")
        r_p1.bold = True
        p_phase.add_run(d_info["phase"])
        p_phase.paragraph_format.space_after = Pt(4)

        # Commits table
        t_comm = doc.add_table(rows=len(d_info["commits"]) + 1, cols=3)
        t_comm.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(t_comm, color="E2E8F0", sz="4")

        # Header
        h_row = t_comm.rows[0]
        h_row.cells[0].width = Inches(1.1)
        h_row.cells[1].width = Inches(1.5)
        h_row.cells[2].width = Inches(3.67)
        h_row.cells[0].paragraphs[0].add_run("Time")
        h_row.cells[1].paragraphs[0].add_run("Author")
        h_row.cells[2].paragraphs[0].add_run("Milestone & Commit")
        format_row(h_row, bg_color="1E3A8A", is_header=True, font_size=9)

        for c_idx, (t_str, a_str, m_str) in enumerate(d_info["commits"]):
            r = t_comm.rows[c_idx + 1]
            r.cells[0].width = Inches(1.1)
            r.cells[1].width = Inches(1.5)
            r.cells[2].width = Inches(3.67)
            r.cells[0].paragraphs[0].add_run(t_str)
            r.cells[1].paragraphs[0].add_run(a_str)
            r.cells[2].paragraphs[0].add_run(m_str)
            bg = "F8FAFC" if c_idx % 2 == 0 else "FFFFFF"
            format_row(r, bg_color=bg, is_header=False, font_size=8.5)

        # Deliverables
        doc.add_paragraph().paragraph_format.space_after = Pt(2)
        p_deliv_hdr = doc.add_paragraph()
        r_dh = p_deliv_hdr.add_run("Key Deliverables & Architectural Impact:")
        r_dh.bold = True
        r_dh.font.size = Pt(9.5)
        p_deliv_hdr.paragraph_format.space_after = Pt(2)

        for item in d_info["deliverables"]:
            p_bullet = doc.add_paragraph(style="List Bullet")
            p_bullet.paragraph_format.space_before = Pt(1)
            p_bullet.paragraph_format.space_after = Pt(2)
            r_b = p_bullet.add_run(item)
            r_b.font.name = "Segoe UI"
            r_b.font.size = Pt(9)
            r_b.font.color.rgb = RGBColor(30, 41, 59)

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # Section 3: Module Evolution Timeline
    add_styled_heading(doc, "Module Evolution Timeline", level=2)
    p_evo = doc.add_paragraph("The lifecycle diagram below traces the release and maturation milestones of the 10 core functional modules across the 27-day development window:")
    p_evo.paragraph_format.space_after = Pt(8)

    evo_img = "docs/images/module_evolution.png"
    if os.path.exists(evo_img):
        doc.add_picture(evo_img, width=Inches(6.27))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.paragraphs[-1].paragraph_format.space_after = Pt(14)

    # Section 4: Contributor Analysis
    add_styled_heading(doc, "Contributor Analysis & Team Breakdown", level=2)
    doc.add_paragraph("Engineering contributions were distributed between two primary engineers, spanning core backend architectures, portal interfaces, logistics algorithms, and quality verification:").paragraph_format.space_after = Pt(6)

    contrib_data = [
        ("Rishab / Code-Cool-2006", "42 Commits (69%)", "Lead Architect, UI/UX & Systems Engineer", [
            ("Modular REST APIs & CLI Commands", "Architected extensible REST API endpoints, management scripts (seed_schools, seed_inventory, seed_academics), and reporting export engines."),
            ("Portal Interfaces & Dashboards", "Engineered Academics Portal, Inventory Portal, and School Management Portal with KPI metric aggregations."),
            ("UI/UX Design System", "Built 3 iterations of modern responsive sidebar, unified global CSS stylesheets, and upgraded tables and cards to modern shadcn aesthetics."),
            ("Authentication & Security", "Created branded Aequs SEZ login interface, session management, and role-based authentication decorators."),
            ("Production DevOps & Deployment", "Configured production containerization (Dockerfile), cloud blueprint (render.yaml), Gunicorn, and Whitenoise static bundling."),
            ("Automated Test Suite", "Created comprehensive 78-case automated testing suite verifying models, permissions, and API endpoints (100% pass rate)."),
            ("Volunteer Management System", "Built complete volunteer management system: CRUD directory, hours tracking, and event participation logging."),
            ("Public QR Sharing & Self-Registration", "Engineered unique tokenized VolunteerFormLink generator, live PNG QR code view, and public mobile signup flow."),
            ("Architectural Audit & Streamlining", "Conducted comprehensive codebase audit, purged 52 dead/backup files (-29,811 lines), unified QR views, and merged PR #1."),
        ]),
        ("Saloni Dalvi / salonidalvi-008", "19 Commits (31%)", "Core Services & Logistics Engineer", [
            ("Initial Architecture Scaffolding", "Scaffolded initial Django project, core schema models, and 13 foundation app packages."),
            ("Distributions & Study Kits", "Developed student benefit distribution services, study kit assembly rules, and stationery handover loggers."),
            ("Academic Filters & Course Master", "Built dynamic CourseMaster model and flexible academic class filters separating degree streams from school grades."),
            ("Enterprise SQL Server Integration", "Configured Microsoft SQL Server ODBC driver and connection logic for enterprise on-prem deployments."),
            ("Internship Management Portal", "Built end-to-end corporate internship portal: company partners, student placements, and milestone trackers."),
            ("Eligibility Engine Fixes", "Resolved critical course misclassification bug and implemented class equivalent resolution (10/10th, PU/PUC)."),
            ("Bulk Upload Workflows", "Developed CSV batch import pipelines for students, schools, academics, and inventory."),
        ]),
    ]

    for name, stats, role, areas in contrib_data:
        add_styled_heading(doc, f"{name} — {stats}", level=3)
        p_r = doc.add_paragraph()
        r_r1 = p_r.add_run("Primary Focus: ")
        r_r1.bold = True
        p_r.add_run(role)
        p_r.paragraph_format.space_after = Pt(4)

        t_c = doc.add_table(rows=len(areas) + 1, cols=2)
        t_c.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(t_c, color="E2E8F0", sz="4")

        h_r = t_c.rows[0]
        h_r.cells[0].width = Inches(2.1)
        h_r.cells[1].width = Inches(4.17)
        h_r.cells[0].paragraphs[0].add_run("Functional Domain")
        h_r.cells[1].paragraphs[0].add_run("Key Architectural Contributions")
        format_row(h_r, bg_color="1E3A8A", is_header=True, font_size=9)

        for a_idx, (dom, desc) in enumerate(areas):
            row = t_c.rows[a_idx + 1]
            row.cells[0].width = Inches(2.1)
            row.cells[1].width = Inches(4.17)
            row.cells[0].paragraphs[0].add_run(dom).bold = True
            row.cells[1].paragraphs[0].add_run(desc)
            bg = "F8FAFC" if a_idx % 2 == 0 else "FFFFFF"
            format_row(row, bg_color=bg, is_header=False, font_size=8.5)

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # Section 5: Development Statistics
    add_styled_heading(doc, "Development Statistics & Repository Metrics", level=2)
    stats_table_data = [
        ("Total Git Commits", "61 commits (+ 1 optimization sprint)"),
        ("Calendar Duration", "27 calendar days (August 12, 2026 – September 07, 2026)"),
        ("Active Engineering Days", "14 distinct active development days"),
        ("Peak Development Sprints", "August 18 (19 commits) & September 05 (12 commits)"),
        ("Core Software Engineers", "2 Primary Contributors (Rishab: 42 commits / 69%, Saloni Dalvi: 19 commits / 31%)"),
        ("Active Django Application Modules", "11 focused functional applications"),
        ("Dead Files Purged (Audit)", "52 files eliminated (-29,811 lines of dead/backup code)"),
        ("Database Models (Active)", "22 relational models with strict foreign keys & constraints"),
        ("Automated Test Suite", "78 comprehensive test cases (100% passing in 5.6 seconds)"),
        ("System Check Status", "0 issues, 0 silenced warnings (Clean system check)"),
        ("UI Portals & Dashboards", "8 specialized operational portals (Executive, Schools, Students, Academics, Eligibility, Inventory, Internships, Volunteers)"),
        ("Supported Database Engines", "SQLite (local development), PostgreSQL (cloud production), Microsoft SQL Server (enterprise on-prem)"),
        ("Supported Deployment Targets", "Docker containerization, Render PaaS, Gunicorn WSGI, Whitenoise"),
    ]

    t_s = doc.add_table(rows=len(stats_table_data) + 1, cols=2)
    t_s.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_s, color="E2E8F0", sz="4")

    h_s = t_s.rows[0]
    h_s.cells[0].width = Inches(2.5)
    h_s.cells[1].width = Inches(3.77)
    h_s.cells[0].paragraphs[0].add_run("Metric")
    h_s.cells[1].paragraphs[0].add_run("Current Repository Value")
    format_row(h_s, bg_color="1E3A8A", is_header=True, font_size=9)

    for idx, (m_lbl, m_val) in enumerate(stats_table_data):
        r = t_s.rows[idx + 1]
        r.cells[0].width = Inches(2.5)
        r.cells[1].width = Inches(3.77)
        r.cells[0].paragraphs[0].add_run(m_lbl).bold = True
        r.cells[1].paragraphs[0].add_run(m_val)
        bg = "F8FAFC" if idx % 2 == 0 else "FFFFFF"
        format_row(r, bg_color=bg, is_header=False, font_size=8.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Section 6: Technology Stack
    add_styled_heading(doc, "Technology Stack & Production Blueprint", level=2)
    tech_data = [
        ("Core Backend Framework", "Python 3.14 / Django 6.1 (Enterprise MVC architecture with atomic DB transactions)"),
        ("Frontend Presentation", "Django Templates (Semantic HTML5), Vanilla CSS design tokens, modern ES6 JavaScript"),
        ("Design System & Aesthetics", "Custom curated design system (Aequs royal blue / slate palette), shadcn-inspired cards, glassmorphism"),
        ("Iconography & Fonts", "Lucide Icons (SVG CDN), Segoe UI / Inter / Montserrat modern typography"),
        ("Relational Databases", "PostgreSQL (Production Cloud), SQLite 3 (Local Development), Microsoft SQL Server (ODBC enterprise)"),
        ("Database ORM & Connectors", "Django ORM, dj-database-url (dynamic cloud config), psycopg2-binary, pyodbc, mssql-django"),
        ("Asset & Media Processing", "Pillow 12.3 (image manipulation, student photos), python-docx (reporting), openpyxl (Excel exports)"),
        ("QR Code Engine", "qrcode 8.2 with high-density Reed-Solomon error correction (Level H)"),
        ("Static File Delivery", "Whitenoise 6.12 (compressed & cached production asset streaming)"),
        ("WSGI Server & Runtime", "Gunicorn 26.2 (asynchronous multi-worker HTTP application server)"),
        ("Containerization & PaaS", "Docker multi-stage builds, Render cloud hosting blueprint (render.yaml)"),
    ]

    t_tech = doc.add_table(rows=len(tech_data) + 1, cols=2)
    t_tech.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_tech, color="E2E8F0", sz="4")

    h_t = t_tech.rows[0]
    h_t.cells[0].width = Inches(2.3)
    h_t.cells[1].width = Inches(3.97)
    h_t.cells[0].paragraphs[0].add_run("Architectural Layer")
    h_t.cells[1].paragraphs[0].add_run("Adopted Technologies & Implementation Details")
    format_row(h_t, bg_color="1E3A8A", is_header=True, font_size=9)

    for idx, (t_l, t_d) in enumerate(tech_data):
        r = t_tech.rows[idx + 1]
        r.cells[0].width = Inches(2.3)
        r.cells[1].width = Inches(3.97)
        r.cells[0].paragraphs[0].add_run(t_l).bold = True
        r.cells[1].paragraphs[0].add_run(t_d)
        bg = "F8FAFC" if idx % 2 == 0 else "FFFFFF"
        format_row(r, bg_color=bg, is_header=False, font_size=8.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Section 7: Development Phases Summary
    add_styled_heading(doc, "Development Phases Summary & Milestone Matrix", level=2)
    p_ph = doc.add_paragraph("Overview of the 10 development phases spanning the project lifecycle, showing active dates, primary functional focus, and commit volume:")
    p_ph.paragraph_format.space_after = Pt(8)

    phase_img = "docs/images/phases_summary.png"
    if os.path.exists(phase_img):
        doc.add_picture(phase_img, width=Inches(6.27))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.paragraphs[-1].paragraph_format.space_after = Pt(10)

    phases_matrix = [
        ("Phase 1", "Aug 12", "Project Foundation & Scaffolding", "Initial Django setup, custom User model with 5 RBAC roles, core student/school models", "2 commits"),
        ("Phase 2", "Aug 13", "REST APIs & Management Commands", "InventoryItem & StockTransaction models, Academics & Inventory portals, seed commands", "1 commit"),
        ("Phase 3", "Aug 18", "Major Feature Sprint & UI/UX Overhaul", "Internships, Events, Volunteers, 3-tier sidebar evolution, global CSS design, Docker/Render deploy", "19 commits"),
        ("Phase 4", "Aug 24", "Authentication & Bulk Upload Workflows", "Aequs SEZ branded login screen, CSV bulk import pipelines for 4 modules, student selection rules", "3 commits"),
        ("Phase 5", "Aug 25–27", "Academic Enhancements & Enterprise DB", "CourseMaster dynamic filter, Microsoft SQL Server ODBC integration, academic form refinement", "6 commits"),
        ("Phase 6", "Aug 28", "School Portal & Automated Test Suite", "School Management Portal, GradeStrength matrices, comprehensive 78-case API testing suite", "6 commits"),
        ("Phase 7", "Aug 31", "Eligibility Engine & Class Resolvers", "User manual and timeline docs, college vs school course separation bugfix, class equivalent resolvers", "5 commits"),
        ("Phase 8", "Sep 01–02", "Inventory Logistics & PR #1 Integration", "Event resource request link, inventory bulk upload repair, stock status tags, PR #1 merge", "5 commits"),
        ("Phase 9", "Sep 04–05", "Volunteer System & Public Registration", "JSON reporting API, complete volunteer portal, tokenized form link generator, live QR codes", "14 commits"),
        ("Phase 10", "Sep 07", "Architecture Audit & Optimization Sprint", "Codebase audit: -29,811 lines of dead/backup code removed, 5 skeleton apps purged, unified QR views", "1 sprint"),
    ]

    t_ph = doc.add_table(rows=len(phases_matrix) + 1, cols=5)
    t_ph.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_ph, color="E2E8F0", sz="4")

    h_ph = t_ph.rows[0]
    h_ph.cells[0].width = Inches(0.8)
    h_ph.cells[1].width = Inches(0.9)
    h_ph.cells[2].width = Inches(1.8)
    h_ph.cells[3].width = Inches(2.1)
    h_ph.cells[4].width = Inches(0.67)
    h_ph.cells[0].paragraphs[0].add_run("Phase")
    h_ph.cells[1].paragraphs[0].add_run("Dates")
    h_ph.cells[2].paragraphs[0].add_run("Focus Area")
    h_ph.cells[3].paragraphs[0].add_run("Key Deliverables")
    h_ph.cells[4].paragraphs[0].add_run("Volume")
    format_row(h_ph, bg_color="1E3A8A", is_header=True, font_size=8.5)

    for idx, (p_id, p_dt, p_fc, p_dl, p_vol) in enumerate(phases_matrix):
        r = t_ph.rows[idx + 1]
        r.cells[0].width = Inches(0.8)
        r.cells[1].width = Inches(0.9)
        r.cells[2].width = Inches(1.8)
        r.cells[3].width = Inches(2.1)
        r.cells[4].width = Inches(0.67)
        r.cells[0].paragraphs[0].add_run(p_id).bold = True
        r.cells[1].paragraphs[0].add_run(p_dt)
        r.cells[2].paragraphs[0].add_run(p_fc).bold = True
        r.cells[3].paragraphs[0].add_run(p_dl)
        r.cells[4].paragraphs[0].add_run(p_vol)
        bg = "F8FAFC" if idx % 2 == 0 else "FFFFFF"
        format_row(r, bg_color=bg, is_header=False, font_size=8)

    doc.add_paragraph().paragraph_format.space_after = Pt(16)

    # Footer notice
    footer_p = doc.add_paragraph()
    footer_p.paragraph_format.space_before = Pt(16)
    footer_p.paragraph_format.space_after = Pt(0)
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_foot = footer_p.add_run("Aequs EduTrack Project Timeline • Generated from Repository Git Log on September 07, 2026\n© 2026 Aequs Foundation. All rights reserved.")
    r_foot.font.name = "Segoe UI"
    r_foot.font.size = Pt(8.5)
    r_foot.font.color.rgb = RGBColor(100, 116, 139)

    out_path = "Aequs EduTrack — Project Timeline.docx"
    doc.save(out_path)
    print(f"Document successfully created and saved to: {out_path}")

if __name__ == "__main__":
    build_timeline_document()
