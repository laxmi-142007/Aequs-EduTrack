from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()


class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    category = models.CharField(max_length=50, default="GENERAL")
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.action}"


def log_activity(user_or_request, action, category="GENERAL", details=""):
    user = None
    if hasattr(user_or_request, "user"):
        user = user_or_request.user if user_or_request.user.is_authenticated else None
    elif isinstance(user_or_request, User):
        user = user_or_request

    return ActivityLog.objects.create(
        user=user,
        action=action,
        category=category.upper(),
        details=details
    )


class Report(models.Model):
    class ReportType(models.TextChoices):
        STUDENT_DEMOGRAPHICS = "STUDENT_DEMOGRAPHICS", "Student Demographics & Enrollment"
        BENEFIT_ELIGIBILITY = "BENEFIT_ELIGIBILITY", "Benefit Eligibility (Kits, Laptops, Books)"
        DISTRIBUTION_SUMMARY = "DISTRIBUTION_SUMMARY", "Inventory & Distribution Records"
        SCHOOL_INFRASTRUCTURE = "SCHOOL_INFRASTRUCTURE", "School Infrastructure & Reach"
        ACTIVITY_AUDIT = "ACTIVITY_AUDIT", "System Activity & Audit Logs"
        CUSTOM = "CUSTOM", "Custom Operational Report"

    class Visibility(models.TextChoices):
        PUBLIC = "PUBLIC", "All Users (Public)"
        ROLES = "ROLES", "Specific System Roles"
        GROUPS = "GROUPS", "Specific User Groups"
        CREATOR = "CREATOR", "Private (Only Me & Super Admins)"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft / In Review"
        PUBLISHED = "PUBLISHED", "Published / Final"
        ARCHIVED = "ARCHIVED", "Archived"

    title = models.CharField(max_length=200)
    report_type = models.CharField(
        max_length=40,
        choices=ReportType.choices,
        default=ReportType.STUDENT_DEMOGRAPHICS,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PUBLISHED,
        blank=True,
    )
    description = models.TextField(blank=True)
    summary_notes = models.TextField(
        blank=True,
        help_text="Executive summary, audit findings, or custom commentary",
    )
    attachment = models.FileField(
        upload_to="reports/attachments/",
        blank=True,
        null=True,
        help_text="Attach PDF report, signed documentation, or supporting files",
    )
    row_limit = models.PositiveIntegerField(
        default=100,
        blank=True,
        null=True,
        help_text="Maximum records to include (0 for all matching records)",
    )
    academic_year = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text="e.g. 2024-2025 or leave blank for all years",
    )
    category_filter = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Optional category or benefit type filter",
    )
    date_from = models.DateField(blank=True, null=True)
    date_to = models.DateField(blank=True, null=True)

    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    allowed_roles = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Comma-separated role codes e.g. SUPER_ADMIN,ADMIN,ACCOUNTANT",
    )
    allowed_groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name="accessible_reports",
        help_text="Groups permitted to view this report",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_reports",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Report"
        verbose_name_plural = "Reports"

    def __str__(self):
        return f"{self.title} ({self.get_report_type_display()})"

    @property
    def has_attachment(self):
        return bool(self.attachment and hasattr(self.attachment, "name") and self.attachment.name)

    @property
    def is_pdf(self):
        if not self.has_attachment:
            return False
        return self.attachment.name.lower().endswith(".pdf")

    @property
    def attachment_filename(self):
        if not self.has_attachment:
            return ""
        import os
        return os.path.basename(self.attachment.name)

    @property
    def attachment_size(self):
        if not self.has_attachment:
            return ""
        try:
            size = self.attachment.size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{round(size / 1024, 1)} KB"
            else:
                return f"{round(size / (1024 * 1024), 1)} MB"
        except Exception:
            return ""

    def apply_limit(self, qs):
        # ponytail: simple slice over DB pagination since reports view top N records
        if self.row_limit and self.row_limit > 0:
            return qs[:self.row_limit]
        return qs

    def is_visible_to(self, user):
        """
        Check if a given user has permission to view this report.
        """
        if not user or not user.is_authenticated:
            return False

        # Superusers and admins can see all reports
        if getattr(user, "is_superuser", False) or getattr(user, "is_admin", False):
            return True

        # Creator always has access
        if self.created_by_id == user.id:
            return True

        if self.visibility == self.Visibility.PUBLIC:
            return True

        if self.visibility == self.Visibility.ROLES:
            if not self.allowed_roles:
                return False
            allowed_list = [r.strip() for r in self.allowed_roles.split(",") if r.strip()]
            user_role = getattr(user, "role", "")
            return user_role in allowed_list

        if self.visibility == self.Visibility.GROUPS:
            user_group_ids = user.groups.values_list("id", flat=True)
            return self.allowed_groups.filter(id__in=user_group_ids).exists()

        if self.visibility == self.Visibility.CREATOR:
            return self.created_by_id == user.id

        return False

    def get_access_display(self):
        """
        Returns a friendly formatted description of who has access.
        """
        if self.visibility == self.Visibility.PUBLIC:
            return "All Users"
        elif self.visibility == self.Visibility.ROLES:
            if not self.allowed_roles:
                return "No Roles Specified"
            role_dict = dict(User.get_all_role_choices()) if hasattr(User, "get_all_role_choices") else {}
            roles = [role_dict.get(r.strip(), r.strip().title()) for r in self.allowed_roles.split(",") if r.strip()]
            return f"Roles: {', '.join(roles)}"
        elif self.visibility == self.Visibility.GROUPS:
            groups = list(self.allowed_groups.values_list("name", flat=True))
            if not groups:
                return "No Groups Specified"
            return f"Groups: {', '.join(groups)}"
        elif self.visibility == self.Visibility.CREATOR:
            creator_name = self.created_by.get_full_name() or self.created_by.username if self.created_by else "Creator"
            return f"Private ({creator_name})"
        return self.get_visibility_display()

    def generate_data(self):
        """
        Queries live records matching the report definition and returns:
        - kpis: list of {label, value, sub}
        - headers: list of column names
        - rows: list of lists representing table data
        """
        kpis = []
        headers = []
        rows = []

        if self.report_type == self.ReportType.STUDENT_DEMOGRAPHICS:
            from students.models import Student
            qs = Student.objects.select_related("school").all()
            total = qs.count()
            active = qs.filter(status=Student.Status.ACTIVE).count()
            male = qs.filter(gender="MALE").count()
            female = qs.filter(gender="FEMALE").count()

            kpis = [
                {"label": "Total Students", "value": total, "sub": "Enrolled in EduTrack"},
                {"label": "Active Students", "value": active, "sub": f"{round((active/total*100) if total else 0)}% of total"},
                {"label": "Boys / Girls", "value": f"{male} / {female}", "sub": "Gender distribution"},
            ]
            headers = ["Admission No", "Student Name", "School", "Class", "Gender", "Status"]
            for s in self.apply_limit(qs):
                rows.append([
                    s.admission_number,
                    s.student_name,
                    s.school.name if s.school else "—",
                    f"{s.current_class} {s.section}".strip(),
                    s.get_gender_display(),
                    s.get_status_display(),
                ])

        elif self.report_type == self.ReportType.BENEFIT_ELIGIBILITY:
            from eligibility.models import EligibilityRecord, BenefitType
            qs = EligibilityRecord.objects.select_related("student", "student__school").filter(eligible=True)
            if self.academic_year:
                qs = qs.filter(academic_year=self.academic_year)
            if self.category_filter:
                qs = qs.filter(benefit_type=self.category_filter)

            total_rec = qs.count()
            kits = qs.filter(benefit_type=BenefitType.STUDY_KIT).count()
            laptops = qs.filter(benefit_type=BenefitType.LAPTOP).count()
            books = qs.filter(benefit_type=BenefitType.BOOK).count()

            kpis = [
                {"label": "Total Eligible Records", "value": total_rec, "sub": f"Year: {self.academic_year or 'All'}"},
                {"label": "Study Kits Eligible", "value": kits, "sub": "Standard kits"},
                {"label": "Laptops Eligible", "value": laptops, "sub": "High merit students"},
                {"label": "Books Eligible", "value": books, "sub": "Textbook sets"},
            ]
            headers = ["Student Name", "School", "Benefit Type", "Academic Year", "Eligible", "Criteria / Reason"]
            for r in self.apply_limit(qs):
                rows.append([
                    r.student.student_name if r.student else "—",
                    r.student.school.name if r.student and r.student.school else "—",
                    r.get_benefit_type_display(),
                    r.academic_year,
                    "Yes" if r.eligible else "No",
                    getattr(r, "reason", "") or "—",
                ])

        elif self.report_type == self.ReportType.DISTRIBUTION_SUMMARY:
            from distributions.models import Distribution
            qs = Distribution.objects.select_related("student", "school", "inventory_item").all()
            if self.category_filter:
                qs = qs.filter(benefit_type=self.category_filter)

            total_d = qs.count()
            student_d = qs.filter(recipient_type="STUDENT").count()
            school_d = qs.filter(recipient_type="SCHOOL").count()

            kpis = [
                {"label": "Total Distributions", "value": total_d, "sub": "All recorded dispatches"},
                {"label": "Student Beneficiaries", "value": student_d, "sub": "Direct students"},
                {"label": "School Essentials", "value": school_d, "sub": "School level"},
            ]
            headers = ["ID", "Recipient Type", "Beneficiary", "Benefit Type", "Item / Details"]
            for d in self.apply_limit(qs):
                beneficiary = d.student.student_name if d.student else (d.school.name if d.school else "—")
                item_name = d.inventory_item.item_name if d.inventory_item else (d.essential_item_type or "—")
                rows.append([
                    f"#{d.id}",
                    d.get_recipient_type_display(),
                    beneficiary,
                    d.get_benefit_type_display(),
                    item_name,
                ])

        elif self.report_type == self.ReportType.SCHOOL_INFRASTRUCTURE:
            from schools.models import School
            qs = School.objects.all()
            total_schools = qs.count()
            districts = qs.values_list("district", flat=True).distinct().count()

            kpis = [
                {"label": "Partner Schools", "value": total_schools, "sub": "Active government schools"},
                {"label": "Districts Covered", "value": districts, "sub": "Coverage reach"},
            ]
            headers = ["School Code", "School Name", "District", "Taluk", "Headmaster", "Contact"]
            for sch in self.apply_limit(qs):
                rows.append([
                    sch.udise_code,
                    sch.name,
                    sch.district or "—",
                    sch.taluk or "—",
                    sch.headmaster_name or "—",
                    sch.phone or "—",
                ])

        elif self.report_type == self.ReportType.ACTIVITY_AUDIT:
            qs = ActivityLog.objects.select_related("user").all()
            if self.category_filter:
                qs = qs.filter(category=self.category_filter.upper())
            if self.date_from:
                qs = qs.filter(timestamp__date__gte=self.date_from)
            if self.date_to:
                qs = qs.filter(timestamp__date__lte=self.date_to)

            total_events = qs.count()
            users_count = qs.values_list("user", flat=True).distinct().count()

            kpis = [
                {"label": "Total Logged Events", "value": total_events, "sub": "Audit records"},
                {"label": "Active Actors", "value": users_count, "sub": "Distinct users"},
            ]
            headers = ["Timestamp", "Category", "Action Description", "User", "Details"]
            for l in self.apply_limit(qs):
                rows.append([
                    l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    l.category,
                    l.action,
                    l.user.username if l.user else "System Admin",
                    l.details or "—",
                ])

        else:  # CUSTOM
            from students.models import Student
            from eligibility.models import EligibilityRecord
            st_count = Student.objects.filter(status=Student.Status.ACTIVE).count()
            el_count = EligibilityRecord.objects.filter(eligible=True).count()
            kpis = [
                {"label": "Active Students", "value": st_count, "sub": "Enrollment pool"},
                {"label": "Eligible Benefits", "value": el_count, "sub": "Verified students"},
            ]
            headers = ["Module Metric", "Summary Total", "Scope"]
            rows = [
                ["Active Students", str(st_count), "All Partner Schools"],
                ["Benefit Grants", str(el_count), "Current Academic Cycle"],
            ]

        return {
            "kpis": kpis,
            "headers": headers,
            "rows": rows,
            "total_records": len(rows),
        }
