from django.contrib import admin
from .models import Volunteer, VolunteerActivity, EventParticipation


@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "email",
        "phone",
        "qualification",
        "status",
        "registration_date",
    )

    list_filter = (
        "status",
        "gender",
        "registration_date",
    )

    search_fields = (
        "first_name",
        "last_name",
        "email",
        "phone",
        "qualification",
        "skills",
    )

    readonly_fields = (
        "registration_date",
        "created_at",
        "updated_at",
    )


@admin.register(VolunteerActivity)
class VolunteerActivityAdmin(admin.ModelAdmin):
    list_display = (
        "volunteer",
        "activity_name",
        "activity_date",
        "status",
    )

    list_filter = (
        "status",
        "activity_date",
    )

    search_fields = (
        "volunteer__first_name",
        "volunteer__last_name",
        "activity_name",
    )


@admin.register(EventParticipation)
class EventParticipationAdmin(admin.ModelAdmin):
    list_display = (
        "volunteer",
        "event",
        "role",
        "participation_status",
        "hours_contributed",
        "assigned_at",
    )

    list_filter = (
        "participation_status",
        "event",
    )

    search_fields = (
        "volunteer__first_name",
        "volunteer__last_name",
        "event__title",
        "role",
    )
