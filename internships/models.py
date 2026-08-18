from django.db import models
from django.utils import timezone
from students.models import Student
from schools.models import School


class Department(models.TextChoices):
    AEROSPACE_ENG = "AEROSPACE_ENG", "Aerospace Engineering"
    PRECISION_MANUFACTURING = "PRECISION_MANUFACTURING", "Precision Manufacturing & CNC"
    QUALITY_ASSURANCE = "QUALITY_ASSURANCE", "Quality Assurance & Metrology"
    IT_AND_SOFTWARE = "IT_AND_SOFTWARE", "Information Technology & Systems"
    SUPPLY_CHAIN = "SUPPLY_CHAIN", "Supply Chain & Logistics"
    TOOL_AND_DIE = "TOOL_AND_DIE", "Tool & Die Making"
    FINANCE_OPERATIONS = "FINANCE_OPERATIONS", "Finance & Commercial Operations"
    HUMAN_RESOURCES = "HUMAN_RESOURCES", "Human Resources & CSR"
    OTHER = "OTHER", "General / Technical Operations"


class InternshipProgram(models.Model):
    """
    Defines corporate internship tracks and batch postings offered by Aequs & industry partners.
    """
    objects = models.Manager()

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open for Applications"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CLOSED = "CLOSED", "Closed / Archived"

    title = models.CharField(
        max_length=200,
        help_text="e.g. Aequs Aerospace Precision Engineering Internship",
    )
    program_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="e.g. AEQ-INT-2026-01",
    )
    company_name = models.CharField(
        max_length=150,
        default="Aequs Aerospace SEZ",
    )
    department = models.CharField(
        max_length=50,
        choices=Department.choices,
        default=Department.PRECISION_MANUFACTURING,
    )
    location = models.CharField(
        max_length=150,
        default="Belagavi SEZ, Karnataka",
    )
    duration_months = models.PositiveIntegerField(
        default=3,
        help_text="Duration in months",
    )
    stipend_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=8000.00,
        help_text="Monthly stipend in INR",
    )
    total_slots = models.PositiveIntegerField(
        default=15,
        help_text="Maximum candidate capacity",
    )
    academic_year = models.CharField(
        max_length=20,
        default="2026-27",
    )
    start_date = models.DateField(
        null=True,
        blank=True,
    )
    end_date = models.DateField(
        null=True,
        blank=True,
    )
    eligibility_criteria = models.TextField(
        blank=True,
        default="Degree / Diploma / Vocational candidates with technical or science background.",
    )
    description = models.TextField(
        blank=True,
    )
    mentor_in_charge = models.CharField(
        max_length=150,
        blank=True,
    )
    mentor_contact = models.CharField(
        max_length=100,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Internship Program"
        verbose_name_plural = "Internship Programs"

    def __str__(self):
        return f"{self.title} ({self.program_code}) - {self.company_name}"

    @property
    def enrolled_count(self):
        return self.placements.filter(
            status__in=[
                InternshipPlacement.Status.SELECTED,
                InternshipPlacement.Status.IN_PROGRESS,
                InternshipPlacement.Status.COMPLETED,
            ]
        ).count()

    @property
    def available_slots(self):
        return max(0, self.total_slots - self.enrolled_count)


class InternshipPlacement(models.Model):
    """
    Individual student placement/internship record linking a student to an internship track.
    """
    objects = models.Manager()

    class Status(models.TextChoices):
        APPLIED = "APPLIED", "Applied / Nominated"
        SHORTLISTED = "SHORTLISTED", "Shortlisted"
        INTERVIEWING = "INTERVIEWING", "Interview Scheduled"
        SELECTED = "SELECTED", "Selected / Active"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed Successfully"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"
        TERMINATED = "TERMINATED", "Terminated"

    class PerformanceGrade(models.TextChoices):
        OUTSTANDING = "OUTSTANDING", "Outstanding (A+)"
        EXCELLENT = "EXCELLENT", "Excellent (A)"
        VERY_GOOD = "VERY_GOOD", "Very Good (B+)"
        GOOD = "GOOD", "Good (B)"
        SATISFACTORY = "SATISFACTORY", "Satisfactory (C)"
        PENDING = "PENDING", "Evaluation Pending"

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="internship_placements",
    )
    program = models.ForeignKey(
        InternshipProgram,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="placements",
    )
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internship_placements",
    )
    academic_year = models.CharField(
        max_length=20,
        default="2026-27",
    )
    department = models.CharField(
        max_length=50,
        choices=Department.choices,
        default=Department.PRECISION_MANUFACTURING,
    )
    company_name = models.CharField(
        max_length=150,
        default="Aequs Aerospace SEZ",
    )
    project_title = models.CharField(
        max_length=200,
        blank=True,
        help_text="e.g. CNC Machine Calibration & Quality Tolerance Optimization",
    )

    # Dates
    start_date = models.DateField(
        default=timezone.localdate,
    )
    end_date = models.DateField(
        null=True,
        blank=True,
    )

    # Financials & Mentor
    stipend_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=8000.00,
        help_text="Monthly stipend in INR",
    )
    mentor_name = models.CharField(
        max_length=150,
        blank=True,
    )
    mentor_email = models.EmailField(
        blank=True,
    )
    mentor_phone = models.CharField(
        max_length=20,
        blank=True,
    )

    # Status & Progress
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SELECTED,
    )
    attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100.00,
        null=True,
        blank=True,
    )
    performance_grade = models.CharField(
        max_length=20,
        choices=PerformanceGrade.choices,
        default=PerformanceGrade.PENDING,
    )

    # Certification
    certificate_issued = models.BooleanField(
        default=False,
    )
    certificate_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )
    certificate_issue_date = models.DateField(
        null=True,
        blank=True,
    )

    evaluation_feedback = models.TextField(
        blank=True,
        help_text="Supervisor performance remarks & learning milestones achieved",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-start_date", "-created_at"]
        verbose_name = "Internship Placement"
        verbose_name_plural = "Internship Placements"

    def __str__(self):
        title = self.project_title or (self.program.title if self.program else "Industrial Internship")
        return f"{self.student.student_name} - {title} ({self.get_status_display()})"


class InternshipMilestone(models.Model):
    """
    Weekly or monthly milestone log for an intern's project deliverables.
    """
    objects = models.Manager()

    class MilestoneStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_REVIEW = "IN_REVIEW", "Under Mentor Review"
        APPROVED = "APPROVED", "Approved / Completed"
        NEEDS_REVISION = "NEEDS_REVISION", "Needs Revision"

    placement = models.ForeignKey(
        InternshipPlacement,
        on_delete=models.CASCADE,
        related_name="milestones",
    )
    title = models.CharField(
        max_length=200,
        help_text="e.g. Week 4: CAD Blueprint Modelling & Simulation",
    )
    due_date = models.DateField(
        null=True,
        blank=True,
    )
    completed_date = models.DateField(
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=MilestoneStatus.choices,
        default=MilestoneStatus.PENDING,
    )
    deliverables_url = models.URLField(
        blank=True,
        help_text="Link to reports or project repository",
    )
    mentor_comments = models.TextField(
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["due_date", "created_at"]

    def __str__(self):
        return f"{self.placement.student.student_name} - {self.title} ({self.get_status_display()})"
