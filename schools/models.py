from django.db import models


class School(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    AFFILIATION_CHOICES = [
        ("CBSE", "CBSE"),
        ("State", "State Board"),
        ("ICSE", "ICSE"),
    ]

    name = models.CharField(max_length=200)

    udise_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Government school UDISE code",
    )

    address = models.TextField(
        blank=True,
        default="",
    )

    district = models.CharField(max_length=100)

    taluk = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    village = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    pincode = models.CharField(
        max_length=10,
        blank=True,
        default="",
    )

    phone = models.CharField(
        max_length=25,
        blank=True,
        default="",
    )

    email = models.EmailField(
        blank=True,
        default="",
    )

    website = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    headmaster_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    headmaster_phone = models.CharField(
        max_length=25,
        blank=True,
        default="",
    )

    headmaster_qualification = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    headmaster_experience = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=0,
    )

    headmaster_photo = models.ImageField(
        upload_to="headmasters/",
        blank=True,
        null=True,
    )

    affiliation = models.CharField(
        max_length=50,
        choices=AFFILIATION_CHOICES,
        default="State",
        blank=True,
    )

    student_strength = models.PositiveIntegerField(
        default=0,
    )

    established_date = models.DateField(
        null=True,
        blank=True,
    )

    established_year = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"{self.name} ({self.udise_code})"


class SchoolMilestone(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="milestones",
    )
    title = models.CharField(max_length=255)
    year_or_date = models.CharField(max_length=100, blank=True, default="")
    details = models.TextField(blank=True, default="")
    impact = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.school.name} - {self.title}"


class SchoolResource(models.Model):
    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Delivered", "Delivered"),
        ("In Progress", "In Progress"),
        ("Pending", "Pending"),
    ]

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="resources",
    )
    resource_name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="Active")
    quantity = models.PositiveIntegerField(default=1)
    last_updated_note = models.CharField(max_length=150, blank=True, default="")
    details = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.school.name} - {self.resource_name} ({self.status})"


class GradeStrength(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="grade_strengths",
    )
    grade_level = models.CharField(max_length=50)
    male_students = models.PositiveIntegerField(default=0)
    female_students = models.PositiveIntegerField(default=0)
    total_students = models.PositiveIntegerField(default=0)
    change_vs_last_year = models.CharField(max_length=20, default="0")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def save(self, *args, **kwargs):
        self.total_students = self.male_students + self.female_students
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.school.name} - {self.grade_level}: {self.total_students}"