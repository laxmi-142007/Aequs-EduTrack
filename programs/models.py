from django.db import models
from django.utils import timezone
from schools.models import School
from students.models import Student


# ============================================================================
# 1. NGO PARTNER MODEL (Module 5: NGO Management)
# ============================================================================

class NGO(models.Model):
    """
    Manages partner NGOs (Pratham, Agastya, Youth for Seva, etc.)
    and connects them to schools, programs, and student cohorts.
    """
    name = models.CharField(max_length=150, unique=True, help_text="e.g. Pratham, Agastya International Foundation, Youth for Seva")
    code = models.CharField(max_length=50, unique=True, help_text="e.g. PRATHAM, AGASTYA, YFS")
    contact_person = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    focus_areas = models.CharField(max_length=255, blank=True, help_text="e.g. Foundational Literacy & Numeracy, Hands-on STEM Labs, Volunteer Mentorship")
    headquarters = models.CharField(max_length=150, blank=True, default="Karnataka")
    partner_schools = models.ManyToManyField(School, related_name="partner_ngos", blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Partner NGO"
        verbose_name_plural = "Partner NGOs"

    def __str__(self):
        return self.name

    @property
    def code_lower(self):
        return self.code.lower() if self.code else ""

    @property
    def total_programs(self):
        return self.programs.filter(is_archived=False).count()

    @property
    def total_ev_sessions(self):
        return self.ev_sessions.filter(is_archived=False).count()


# ============================================================================
# 2. LOCATION MASTER MODEL (Module 16: Location Management)
# ============================================================================

class Location(models.Model):
    """
    Central Location Master representing clusters, campuses, hubs, and field centers.
    Allows centralized location management and multi-select across projects & programs.
    """
    name = models.CharField(max_length=200, help_text="Facility, campus, school center or venue name")
    code = models.CharField(max_length=50, unique=True, help_text="e.g. LOC-BGV-01")
    district = models.CharField(max_length=100, default="Belagavi")
    taluk = models.CharField(max_length=100, blank=True, default="")
    village_or_town = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, default="Karnataka")
    pincode = models.CharField(max_length=10, blank=True, default="")
    address = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["district", "name"]
        verbose_name = "Location"
        verbose_name_plural = "Locations"

    def __str__(self):
        parts = [self.name, self.taluk, self.district]
        return " — ".join(p for p in parts if p)


# ============================================================================
# 3. PROJECT MODEL (Module 7: Project Tab & Project-Based Tracking)
# ============================================================================

class Project(models.Model):
    """
    Centralized project tracking connecting schools, cohorts, NGOs,
    locations, inventory, volunteers, budgets, and milestones.
    """
    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        ACTIVE = "ACTIVE", "Active"
        ON_HOLD = "ON_HOLD", "On Hold"
        COMPLETED = "COMPLETED", "Completed"
        ARCHIVED = "ARCHIVED", "Archived"

    name = models.CharField(max_length=200, help_text="e.g. STEM for Rural Schools, Digital Literacy Drive 2026")
    code = models.CharField(max_length=50, unique=True, blank=True, help_text="e.g. PRJ-2026-001 (auto-generated if left blank)")
    description = models.TextField(blank=True)
    ngo = models.ForeignKey(NGO, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects")
    target_schools = models.ManyToManyField(School, related_name="associated_projects", blank=True)
    locations = models.ManyToManyField(Location, related_name="projects", blank=True, help_text="Select one or more operational locations")
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    allocated_budget = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Allocated CSR funding in INR")
    spent_budget = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Actual expenditure in INR")
    lead_coordinator = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "name"]
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def __str__(self):
        return f"{self.name} ({self.code})"

    @classmethod
    def generate_next_code(cls, year=None):
        if not year:
            year = timezone.localdate().year
        prefix = f"PRJ-{year}-"
        existing_codes = list(cls.objects.filter(code__startswith=prefix).values_list("code", flat=True))
        max_seq = 0
        for c in existing_codes:
            try:
                seq = int(c.split("-")[-1])
                if seq > max_seq:
                    max_seq = seq
            except (ValueError, IndexError):
                pass
        next_seq = max_seq + 1
        candidate = f"{prefix}{next_seq:03d}"
        while cls.objects.filter(code=candidate).exists():
            next_seq += 1
            candidate = f"{prefix}{next_seq:03d}"
        return candidate

    def save(self, *args, **kwargs):
        if not self.code or not self.code.strip():
            year = self.start_date.year if self.start_date else timezone.localdate().year
            self.code = self.generate_next_code(year=year)
        else:
            self.code = self.code.strip()
        super().save(*args, **kwargs)

    @property
    def budget_utilization_pct(self):
        if self.allocated_budget > 0:
            return round((self.spent_budget / self.allocated_budget) * 100, 1)
        return 0.0



# ============================================================================
# 3. PROGRAM MODEL WITH MANDATORY LOCATION (Module 11 & Module 16)
# ============================================================================

class Program(models.Model):
    """
    Specific operational program under a project or NGO.
    Requires an explicit, mandatory location field across all entries.
    """
    class Category(models.TextChoices):
        STEM = "STEM", "Hands-on Science & STEM"
        FLN = "FLN", "Foundational Literacy & Numeracy"
        DIGITAL = "DIGITAL", "Digital Skills & Labs"
        EV_CLASS = "EV_CLASS", "Exposure Visit & EV Classes"
        HEALTH = "HEALTH", "Health, Hygiene & Nutrition"
        SCHOLARSHIP = "SCHOLARSHIP", "Scholarship & Mentorship"
        VOCATIONAL = "VOCATIONAL", "Vocational & Industrial Readiness"
        OTHER = "OTHER", "Community & Social Development"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        ARCHIVED = "ARCHIVED", "Archived"

    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="programs")
    ngo = models.ForeignKey(NGO, on_delete=models.SET_NULL, null=True, blank=True, related_name="programs")
    title = models.CharField(max_length=200, help_text="e.g. Agastya Mobile Science Lab Program")
    code = models.CharField(max_length=50, unique=True, help_text="e.g. PROG-AGS-SCI-01")
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.STEM)
    description = models.TextField(blank=True)

    # MANDATORY LOCATION FIELDS (Module 11 Requirement)
    location_name = models.CharField(max_length=200, help_text="Facility, campus, school center or venue name (Mandatory)")
    village_or_town = models.CharField(max_length=100, help_text="Village or Town (Mandatory)")
    taluk = models.CharField(max_length=100, help_text="Taluk / Block (Mandatory)")
    district = models.CharField(max_length=100, default="Belagavi", help_text="District (Mandatory)")
    state = models.CharField(max_length=100, default="Karnataka")
    gps_coordinates = models.CharField(max_length=100, blank=True, help_text="e.g. 15.8497° N, 74.4977° E")
    locations = models.ManyToManyField(Location, related_name="programs", blank=True, help_text="Multi-select operational locations")


    participating_schools = models.ManyToManyField(School, related_name="enrolled_programs", blank=True)
    academic_year = models.CharField(max_length=20, default="2026-27")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Program"
        verbose_name_plural = "Programs"

    def __str__(self):
        return f"{self.title} — {self.location_name}, {self.taluk}"

    @property
    def full_location(self):
        parts = [self.location_name, self.village_or_town, self.taluk, self.district]
        return ", ".join(p for p in parts if p)


# ============================================================================
# 4. DETAILED EV CLASS TRACKING MODEL (Module 4)
# ============================================================================

class EVClassSession(models.Model):
    """
    Detailed tracking for EV (Exposure Visit / Experiential Learning /
    Environmental Education) Classes.
    Tracks session topics, venue, facilitator, attendance, kit materials,
    pre/post assessments, and photos.
    """
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        ARCHIVED = "ARCHIVED", "Archived"

    session_title = models.CharField(max_length=200, help_text="e.g. Science Exposure Visit to Aerospace Hub, Solar Cell Hands-on Class")
    session_code = models.CharField(max_length=50, unique=True, help_text="e.g. EV-2026-001")
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True, related_name="ev_sessions")
    ngo = models.ForeignKey(NGO, on_delete=models.SET_NULL, null=True, blank=True, related_name="ev_sessions")
    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name="ev_sessions")
    grade_level = models.CharField(max_length=50, default="Class 8", help_text="Target grade or class")

    topic = models.CharField(max_length=200, help_text="Curriculum topic or scientific concept covered")
    curriculum_module = models.CharField(max_length=150, blank=True, help_text="e.g. Module 3: Renewable Energy & Physics")
    learning_objectives = models.TextField(blank=True)

    session_date = models.DateField(default=timezone.localdate)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=90)
    facilitator_name = models.CharField(max_length=150, help_text="Instructor, trainer or NGO specialist")
    facilitator_contact = models.CharField(max_length=50, blank=True)

    venue_or_route = models.CharField(max_length=255, help_text="Field visit route, campus science lab, or exhibition venue")
    materials_or_kits_used = models.TextField(blank=True, help_text="STEM kits, test tubes, robotic sensors, microscopes utilized")

    students = models.ManyToManyField(Student, related_name="ev_sessions", blank=True)
    attendee_count = models.PositiveIntegerField(default=0)

    pre_assessment_avg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Pre-session baseline percentage")
    post_assessment_avg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Post-session evaluation percentage")
    student_feedback = models.TextField(blank=True)
    documentation_notes = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-session_date", "-created_at"]
        verbose_name = "EV Class Session"
        verbose_name_plural = "EV Class Sessions"

    def __str__(self):
        return f"{self.session_code} — {self.session_title} ({self.school.name})"

    @property
    def assessment_gain(self):
        if self.pre_assessment_avg is not None and self.post_assessment_avg is not None:
            return round(self.post_assessment_avg - self.pre_assessment_avg, 2)
        return None


# ============================================================================
# 5. SCHOLARSHIP MODEL (Module 8 & Module 9: Government & Employee Special)
# ============================================================================

class Scholarship(models.Model):
    """
    Tracks Foundation scholarships, State/Central government scholarship schemes
    (SSP, NSP), and Aequs Employee Special Child Education Assistance.
    """
    class Category(models.TextChoices):
        FOUNDATION = "FOUNDATION", "Aequs Foundation Merit Scholarship"
        GOVERNMENT = "GOVERNMENT", "Government Scholarship (SSP / NSP)"
        EMPLOYEE_SPECIAL = "EMPLOYEE_SPECIAL", "Aequs Employee Special Child Support"

    class Status(models.TextChoices):
        APPLIED = "APPLIED", "Application Submitted"
        VERIFIED = "VERIFIED", "Documentation Verified"
        SANCTIONED = "SANCTIONED", "Sanctioned / Approved"
        DISBURSED = "DISBURSED", "Disbursed / Credited"
        RENEWAL_DUE = "RENEWAL_DUE", "Renewal Due"
        REJECTED = "REJECTED", "Rejected / Ineligible"
        ARCHIVED = "ARCHIVED", "Archived"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="scholarships")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="scholarships", help_text="Linked Project (Optional)")
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True, related_name="scholarships", help_text="Linked Program (Optional)")
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.FOUNDATION)
    scheme_name = models.CharField(max_length=200, help_text="e.g. Karnataka SSP Pre-Matric, National NSP, Aequs Aerospace Child Grant")
    application_number = models.CharField(max_length=100, unique=True, help_text="Portal application or internal tracking number")
    academic_year = models.CharField(max_length=20, default="2026-27")

    sanctioned_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    disbursed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    disbursement_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)

    # Government Scholarship Verification Details (Module 9)
    aadhaar_verified = models.BooleanField(default=False, help_text="Aadhaar linking & seeding verified")
    income_cert_verified = models.BooleanField(default=False, help_text="Income / Caste certificate verified")
    bank_account_verified = models.BooleanField(default=False, help_text="Bank account & IFSC validated")

    # Employee Special Fields (Module 9)
    employee_code = models.CharField(max_length=50, blank=True, help_text="Aequs employee staff code")
    employee_name = models.CharField(max_length=150, blank=True, help_text="Parent employee name")
    employee_department = models.CharField(max_length=100, blank=True, help_text="e.g. Aerospace CNC, Tool & Die, Quality")
    plant_location = models.CharField(max_length=100, blank=True, default="Belagavi SEZ")

    donor_sponsor = models.CharField(max_length=150, blank=True, default="Aequs Foundation CSR")
    remarks = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Scholarship Record"
        verbose_name_plural = "Scholarship Records"

    def __str__(self):
        return f"{self.get_category_display()} — {self.student.student_name} ({self.scheme_name})"


# ============================================================================
# 6. CSR GRANT & SCHOOL INTEGRATION MODEL (Module 12)
# ============================================================================

class CSRGrant(models.Model):
    """
    Connects CSR funding directly to beneficiary schools, tracking
    infrastructure improvements (smart classrooms, science labs, libraries).
    """
    class FacilityType(models.TextChoices):
        SMART_CLASS = "SMART_CLASS", "Smart Digital Classroom"
        SCIENCE_LAB = "SCIENCE_LAB", "Science & Discovery Lab"
        COMPUTER_LAB = "COMPUTER_LAB", "Computer Education Center"
        LIBRARY = "LIBRARY", "School Library & Reading Corner"
        SPORTS = "SPORTS", "Sports Ground & Physical Edu Kit"
        SANITATION = "SANITATION", "Clean Drinking Water & Sanitation"
        SOLAR = "SOLAR", "Solar Energy Power System"
        OTHER = "OTHER", "Infrastructure Upgrade"

    school = models.ForeignKey(School, on_delete=models.PROTECT, related_name="csr_grants")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="csr_grants")
    title = models.CharField(max_length=200, help_text="e.g. Smart Classroom & High-Tech Science Discovery Center")
    facility_type = models.CharField(max_length=30, choices=FacilityType.choices, default=FacilityType.SMART_CLASS)
    grant_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    completion_date = models.DateField(null=True, blank=True)
    beneficiary_student_count = models.PositiveIntegerField(default=0)
    is_operational = models.BooleanField(default=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "CSR School Grant"
        verbose_name_plural = "CSR School Grants"

    def __str__(self):
        return f"{self.title} — {self.school.name} (₹{self.grant_amount})"


# ============================================================================
# 7. MENTORSHIP SESSION MODEL (Mentorship Program Module)
# ============================================================================

class MentorshipSession(models.Model):
    """
    Connects corporate mentors, volunteer mentors, and students to Projects and Programs.
    Tracks session goals, duration, mentorship feedback, and progress.
    """
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    session_title = models.CharField(max_length=200, help_text="e.g. 1-on-1 Engineering Mentoring, Career Guidance")
    session_code = models.CharField(max_length=50, unique=True, blank=True, help_text="e.g. MNT-2026-001 (auto-generated)")
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="mentorship_sessions")
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True, related_name="mentorship_sessions")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="mentorship_sessions")
    mentor_name = models.CharField(max_length=150, help_text="Corporate mentor or Foundation advisor")
    mentor_email = models.EmailField(blank=True)
    mentor_designation = models.CharField(max_length=150, blank=True, default="Aequs Corporate Mentor")
    session_date = models.DateField(default=timezone.localdate)
    duration_minutes = models.PositiveIntegerField(default=60)
    topic = models.CharField(max_length=200, help_text="Curriculum topic, technical guidance, career roadmap")
    notes = models.TextField(blank=True)
    feedback = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-session_date", "-created_at"]
        verbose_name = "Mentorship Session"
        verbose_name_plural = "Mentorship Sessions"

    def __str__(self):
        return f"{self.session_title} — {self.student.student_name} ({self.mentor_name})"

    def save(self, *args, **kwargs):
        if not self.session_code or not self.session_code.strip():
            year = self.session_date.year if self.session_date else timezone.localdate().year
            count = MentorshipSession.objects.filter(session_date__year=year).count() + 1
            code = f"MNT-{year}-{count:03d}"
            while MentorshipSession.objects.filter(session_code=code).exists():
                count += 1
                code = f"MNT-{year}-{count:03d}"
            self.session_code = code
        super().save(*args, **kwargs)

