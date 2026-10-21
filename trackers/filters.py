import django_filters
from django import forms
from django.db.models import Q
from trackers.models import WeeklyTrackerSession, Programme
from schools.models import School


class WeeklyTrackerSessionFilter(django_filters.FilterSet):
    """
    Comprehensive django-filter FilterSet for Weekly Tracker sessions
    with multi-column sorting, date ranges, and text searches.
    """
    academic_year = django_filters.ChoiceFilter(
        choices=[
            ("2025-26", "2025-26"),
            ("2026-27", "2026-27"),
        ],
        empty_label="All Academic Years",
    )
    programme = django_filters.ChoiceFilter(
        choices=Programme.choices,
        empty_label="All Programmes",
    )
    school = django_filters.ModelChoiceFilter(
        queryset=School.objects.all().order_by("name"),
        empty_label="All Schools",
    )

    def __init__(self, *args, current_ngo=None, **kwargs):
        super().__init__(*args, **kwargs)
        if current_ngo:
            self.filters["school"].queryset = current_ngo.partner_schools.all().order_by("name")
    school_name = django_filters.CharFilter(
        method="filter_school_name",
        label="School Name",
    )
    instructor_name = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Instructor",
    )
    session_type = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Session Type",
    )
    teacher_present = django_filters.BooleanFilter(
        label="Teacher Present",
    )
    date_from = django_filters.DateFilter(
        field_name="session_date",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Date From",
    )
    date_to = django_filters.DateFilter(
        field_name="session_date",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Date To",
    )
    q = django_filters.CharFilter(
        method="filter_universal_search",
        label="Universal Search",
    )

    sort_by = django_filters.OrderingFilter(
        fields=(
            ("session_date", "date"),
            ("school__name", "school"),
            ("programme", "programme"),
            ("instructor_name", "instructor"),
            ("total_exposures", "exposures"),
            ("boys_present", "boys"),
            ("girls_present", "girls"),
        ),
        field_labels={
            "session_date": "Date (Chronological)",
            "school__name": "School Name (Alphabetical)",
            "programme": "Programme",
            "instructor_name": "Instructor",
            "total_exposures": "Total Exposures",
            "boys_present": "Boys",
            "girls_present": "Girls",
        },
    )

    class Meta:
        model = WeeklyTrackerSession
        fields = [
            "academic_year",
            "programme",
            "school",
            "instructor_name",
            "session_type",
            "teacher_present",
        ]

    def filter_school_name(self, queryset, name, value):
        if not value:
            return queryset
        val = value.strip()
        return queryset.filter(
            Q(school__name__icontains=val) |
            Q(raw_location_or_activity__icontains=val)
        )

    def filter_universal_search(self, queryset, name, value):
        if not value:
            return queryset
        val = value.strip()
        return queryset.filter(
            Q(school__name__icontains=val) |
            Q(raw_location_or_activity__icontains=val) |
            Q(instructor_name__icontains=val) |
            Q(topic__icontains=val) |
            Q(session_type__icontains=val) |
            Q(standard__icontains=val)
        )
