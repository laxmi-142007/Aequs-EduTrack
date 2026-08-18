from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AcademicRecord
from eligibility.services import generate_all_eligibility


@receiver(post_save, sender=AcademicRecord)
def academic_record_saved(sender, instance, **kwargs):
    """
    Automatically recalculate eligibility whenever
    an academic record is created or updated.
    """

    generate_all_eligibility(instance.academic_year)
