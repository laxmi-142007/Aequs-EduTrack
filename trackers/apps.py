from django.apps import AppConfig


class TrackersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "trackers"
    verbose_name = "Weekly Trackers & Enrollments"

    def ready(self):
        from django.template import defaultfilters
        _orig = defaultfilters.stringformat

        def _smart_stringformat(value, arg):
            try:
                return ("%" + str(arg)) % (value,)
            except (ValueError, TypeError):
                try:
                    return format(int(value or 0), str(arg))
                except (ValueError, TypeError):
                    return ""

        defaultfilters.stringformat = _smart_stringformat
        defaultfilters.register.filter("stringformat", _smart_stringformat, is_safe=True)
