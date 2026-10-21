from django.db import models
from schools.models import School
from programs.models import NGO

__all__ = ["Programme", "School", "SchoolEnrollment", "WeeklyTrackerSession"]


class Programme(models.TextChoices):
    # Youth for Seva (YFS) Programmes
    CHAAP_JR = "CHAAP_JR", "CHAAP Junior (HHP)"
    CHAAP_YUVA = "CHAAP_YUVA", "CHAAP-Yuva (AHAP)"
    SEP = "SEP", "Student Excel Program (SEP)"
    IGNITE_BGM = "IGNITE_BGM", "IGNITE Belagavi"
    IGNITE_HBL = "IGNITE_HBL", "IGNITE Hubballi"
    NMMS = "NMMS", "NMMS Training"
    CAMP = "CAMP", "Winter & Summer Camp"
    SAP = "SAP", "Student Activity Program (SAP)"

    # Agastya International Foundation Programmes
    MSL = "MSL", "Mobile Science Lab (MSL)"
    AVISHKAR = "AVISHKAR", "Avishkar Science Fair"
    VASANTHA = "VASANTHA", "Vasantha After-School"
    YUVACHARYA = "YUVACHARYA", "Yuvacharya B.Ed Training"

    # Pratham Foundation Programmes
    OPN = "OPN", "One Notebook Program"
    READING = "READING", "Learning & Reading Camp"

    OTHERS = "OTHERS", "Other Programmes"


class SchoolEnrollment(models.Model):
    """
    Normalized school class/standard enrollment metrics extracted from
    programme School Data sheets.
    """
    ngo = models.ForeignKey(
        NGO,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="school_enrollments",
        help_text="Partner NGO managing this school cohort",
    )
    academic_year = models.CharField(
        max_length=20,
        db_index=True,
        help_text="e.g. 2025-26, 2026-27",
    )
    programme = models.CharField(
        max_length=100,
        choices=Programme.choices,
        db_index=True,
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="tracker_enrollments",
    )
    standard = models.CharField(
        max_length=50,
        help_text="e.g. 1st STD, 10th STD",
    )
    boys = models.IntegerField(
        default=0,
    )
    girls = models.IntegerField(
        default=0,
    )
    total = models.IntegerField(
        default=0,
        db_index=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "School Enrollment"
        verbose_name_plural = "School Enrollments"
        ordering = ["academic_year", "programme", "school__name", "standard"]
        constraints = [
            models.UniqueConstraint(
                fields=["ngo", "academic_year", "programme", "school", "standard"],
                name="unique_ngo_academic_programme_school_standard",
            )
        ]

    def __str__(self):
        return f"{self.school.name} - {self.get_programme_display()} ({self.standard}): {self.total}"


class WeeklyTrackerSession(models.Model):
    """
    Granular session-level log extracted from Weekly Tracker sheets across all programmes.
    """
    ngo = models.ForeignKey(
        NGO,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="weekly_sessions",
        help_text="Partner NGO running this program session",
    )
    academic_year = models.CharField(
        max_length=20,
        db_index=True,
        help_text="e.g. 2025-26, 2026-27",
    )
    programme = models.CharField(
        max_length=100,
        choices=Programme.choices,
        db_index=True,
    )
    session_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Resolved calendar date based on Indian academic cycle",
    )
    month_name = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Original month name from sheet (e.g. June, July, Jan)",
    )
    day_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Day of month from sheet",
    )
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="weekly_sessions",
    )
    raw_location_or_activity = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Raw school name, meeting title, or venue from spreadsheet column 2",
    )
    standard = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="e.g. 1st, 10th STD, All",
    )
    division = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Class division/section (A, B, etc.)",
    )
    timing = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Session duration or time slot",
    )
    topic = models.TextField(
        blank=True,
        default="",
        help_text="Session topic or curriculum module covered",
    )
    instructor_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
        db_index=True,
        help_text="Faculty, trainer, or volunteer facilitator",
    )
    session_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
        help_text="Theory, Practical, Camp, Activity, Meeting, etc.",
    )
    boys_present = models.IntegerField(
        default=0,
    )
    girls_present = models.IntegerField(
        default=0,
    )
    total_exposures = models.IntegerField(
        default=0,
        db_index=True,
        help_text="Total student exposures for this session",
    )
    teacher_present = models.BooleanField(
        default=False,
        help_text="Whether school teacher was present during session",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Weekly Tracker Session"
        verbose_name_plural = "Weekly Tracker Sessions"
        ordering = ["-session_date", "-id"]
        indexes = [
            models.Index(
                fields=["academic_year", "programme", "-session_date"],
                name="idx_tracker_ay_prog_date",
            ),
            models.Index(
                fields=["ngo", "academic_year", "-session_date"],
                name="idx_tracker_ngo_ay_date",
            ),
            models.Index(
                fields=["instructor_name", "-session_date"],
                name="idx_tracker_inst_date",
            ),
        ]

    def __str__(self):
        loc = self.school.name if self.school else (self.raw_location_or_activity or "Activity")
        d_str = self.session_date.strftime("%Y-%m-%d") if self.session_date else f"{self.month_name} {self.day_number}"
        return f"[{self.academic_year}] {self.get_programme_display()} - {loc} ({d_str}): {self.total_exposures} exposures"
