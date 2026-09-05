# reports/middleware.py

"""
Central Audit Logging Middleware
================================

This middleware automatically records successful user actions across
the application.

Supported modules include:

    STUDENT
    SCHOOL
    INVENTORY
    EVENT
    ACADEMIC
    ELIGIBILITY
    USER
    AUTH
    REPORT
    DASHBOARD
    GENERAL

Supported actions include:

    CREATE
    UPDATE
    DELETE
    LOGIN
    LOGOUT
    VIEW
    EXPORT
    IMPORT
    OTHER

Examples:

    POST /inventory/api/items/create/
        -> INVENTORY / CREATE

    POST /inventory/api/items/5/delete/
        -> INVENTORY / DELETE

    POST /academics/api/records/3/delete/
        -> ACADEMIC / DELETE

    PUT /students/api/25/
        -> STUDENT / UPDATE

    GET requests are not logged by default because normal page/API
    viewing would otherwise create huge numbers of audit records.
"""

from django.urls import resolve

from .models import ActivityLog


# =============================================================================
# MODULE -> REPORT CATEGORY
# =============================================================================

CATEGORY_MAP = {

    # Students
    "students": "STUDENT",
    "student": "STUDENT",

    # Schools
    "schools": "SCHOOL",
    "school": "SCHOOL",

    # Inventory
    "inventory": "INVENTORY",
    "inventories": "INVENTORY",

    # Events
    "events": "EVENT",
    "event": "EVENT",

    # Academics
    "academics": "ACADEMIC",
    "academic": "ACADEMIC",

    # Eligibility
    "eligibility": "ELIGIBILITY",

    # Reports
    "reports": "REPORT",
    "report": "REPORT",

    # Users
    "users": "USER",
    "user": "USER",
    "accounts": "USER",

    # Authentication
    "auth": "AUTH",
    "authentication": "AUTH",
    "login": "AUTH",
    "logout": "AUTH",

    # Dashboard
    "dashboard": "DASHBOARD",
    "home": "DASHBOARD",

    # Other known modules
    "notifications": "NOTIFICATION",
    "notification": "NOTIFICATION",

    "settings": "SETTINGS",
    "setting": "SETTINGS",

    "benefits": "BENEFIT",
    "benefit": "BENEFIT",

    "attendance": "ATTENDANCE",

    "documents": "DOCUMENT",
    "document": "DOCUMENT",

    "staff": "STAFF",

    "teachers": "TEACHER",
    "teacher": "TEACHER",

    "classes": "CLASS",
    "class": "CLASS",
}


# =============================================================================
# PATHS THAT SHOULD NEVER BE LOGGED
# =============================================================================

IGNORED_PATH_PREFIXES = (
    "/static/",
    "/media/",
    "/favicon.ico",
    "/__debug__/",
)


# =============================================================================
# HTTP METHODS THAT CREATE AUDIT EVENTS
# =============================================================================

AUDITABLE_METHODS = {
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
}


# =============================================================================
# CATEGORY DETECTION
# =============================================================================

def get_category_from_path(path):
    """
    Determine the Reports category from the first URL path segment.

    Example:

        /inventory/api/items/5/delete/
            -> INVENTORY

        /students/api/10/update/
            -> STUDENT

        /academics/api/records/3/delete/
            -> ACADEMIC
    """

    parts = [
        part.lower()
        for part in path.strip("/").split("/")
        if part
    ]

    if not parts:
        return "GENERAL"

    first_part = parts[0]

    return CATEGORY_MAP.get(
        first_part,
        first_part.upper()[:50],
    )


# =============================================================================
# ACTION TYPE DETECTION
# =============================================================================

def get_action_type(method, path):
    """
    Determine the actual action being performed.

    Important:
    Many Django APIs use POST for actions such as delete/edit/create.

    Therefore we inspect the URL before falling back to the HTTP method.

    Example:

        POST /academics/api/records/3/delete/

    is correctly classified as:

        DELETE
    """

    method = method.upper()
    path_lower = path.lower()

    # -------------------------------------------------------------------------
    # LOGIN
    # -------------------------------------------------------------------------

    login_patterns = (
        "/login/",
        "/login",
        "/signin/",
        "/signin",
        "/sign-in/",
        "/sign-in",
    )

    if any(
        pattern in path_lower
        for pattern in login_patterns
    ):
        return ActivityLog.ActionType.LOGIN

    # -------------------------------------------------------------------------
    # LOGOUT
    # -------------------------------------------------------------------------

    logout_patterns = (
        "/logout/",
        "/logout",
        "/signout/",
        "/signout",
        "/sign-out/",
        "/sign-out",
    )

    if any(
        pattern in path_lower
        for pattern in logout_patterns
    ):
        return ActivityLog.ActionType.LOGOUT

    # -------------------------------------------------------------------------
    # DELETE
    # -------------------------------------------------------------------------

    delete_patterns = (
        "/delete/",
        "/delete",
        "/remove/",
        "/remove",
        "/destroy/",
        "/destroy",
        "/delete-item/",
        "/delete-item",
        "/delete-record/",
        "/delete-record",
    )

    if any(
        pattern in path_lower
        for pattern in delete_patterns
    ):
        return ActivityLog.ActionType.DELETE

    # -------------------------------------------------------------------------
    # UPDATE / EDIT
    # -------------------------------------------------------------------------

    update_patterns = (
        "/update/",
        "/update",
        "/edit/",
        "/edit",
        "/modify/",
        "/modify",
        "/change/",
        "/change",
    )

    if any(
        pattern in path_lower
        for pattern in update_patterns
    ):
        return ActivityLog.ActionType.UPDATE

    # -------------------------------------------------------------------------
    # CREATE / ADD
    # -------------------------------------------------------------------------

    create_patterns = (
        "/create/",
        "/create",
        "/add/",
        "/add",
        "/new/",
        "/new",
        "/register/",
        "/register",
    )

    if any(
        pattern in path_lower
        for pattern in create_patterns
    ):
        return ActivityLog.ActionType.CREATE

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    export_patterns = (
        "/export/",
        "/export",
        "/download/",
        "/download",
        "/csv/",
        "/csv",
        "/excel/",
        "/excel",
    )

    if any(
        pattern in path_lower
        for pattern in export_patterns
    ):
        return ActivityLog.ActionType.EXPORT

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    import_patterns = (
        "/import/",
        "/import",
        "/upload/",
        "/upload",
        "/bulk-upload/",
        "/bulk-upload",
        "/bulk_import/",
        "/bulk_import",
    )

    if any(
        pattern in path_lower
        for pattern in import_patterns
    ):
        return ActivityLog.ActionType.IMPORT

    # -------------------------------------------------------------------------
    # HTTP METHOD FALLBACK
    # -------------------------------------------------------------------------

    if method == "DELETE":
        return ActivityLog.ActionType.DELETE

    if method in ("PUT", "PATCH"):
        return ActivityLog.ActionType.UPDATE

    if method == "POST":
        return ActivityLog.ActionType.CREATE

    # GET is not normally audited by the middleware.
    return ActivityLog.ActionType.VIEW


# =============================================================================
# ACTION DESCRIPTION
# =============================================================================

def get_action_description(
    method,
    path,
    action_type,
    category,
):
    """
    Convert the technical URL into a more readable audit description.

    Example:

        POST /academics/api/records/3/delete/

    becomes:

        Deleted academic record #3
    """

    clean_path = path.strip("/")

    parts = [
        part
        for part in clean_path.split("/")
        if part
    ]

    # Try to locate a numeric object ID.
    object_id = None

    for part in parts:

        if part.isdigit():
            object_id = part
            break

    category_label = category.replace(
        "_",
        " "
    ).title()

    # -------------------------------------------------------------------------
    # DELETE
    # -------------------------------------------------------------------------

    if action_type == ActivityLog.ActionType.DELETE:

        if object_id:
            return (
                f"Deleted {category_label} record "
                f"#{object_id}"
            )

        return (
            f"Deleted {category_label} record"
        )

    # -------------------------------------------------------------------------
    # UPDATE
    # -------------------------------------------------------------------------

    if action_type == ActivityLog.ActionType.UPDATE:

        if object_id:
            return (
                f"Updated {category_label} record "
                f"#{object_id}"
            )

        return (
            f"Updated {category_label} record"
        )

    # -------------------------------------------------------------------------
    # CREATE
    # -------------------------------------------------------------------------

    if action_type == ActivityLog.ActionType.CREATE:

        if object_id:
            return (
                f"Created {category_label} record "
                f"#{object_id}"
            )

        return (
            f"Created {category_label} record"
        )

    # -------------------------------------------------------------------------
    # LOGIN
    # -------------------------------------------------------------------------

    if action_type == ActivityLog.ActionType.LOGIN:
        return "User Logged In"

    # -------------------------------------------------------------------------
    # LOGOUT
    # -------------------------------------------------------------------------

    if action_type == ActivityLog.ActionType.LOGOUT:
        return "User Logged Out"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    if action_type == ActivityLog.ActionType.EXPORT:
        return (
            f"Exported {category_label} data"
        )

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    if action_type == ActivityLog.ActionType.IMPORT:
        return (
            f"Imported {category_label} data"
        )

    # -------------------------------------------------------------------------
    # OTHER
    # -------------------------------------------------------------------------

    return (
        f"{method.upper()} {path}"
    )


# =============================================================================
# OBJECT ID EXTRACTION
# =============================================================================

def get_object_id_from_path(path):
    """
    Extract the first numeric ID from a URL.

    Example:

        /academics/api/records/3/delete/

    returns:

        3
    """

    parts = [
        part
        for part in path.strip("/").split("/")
        if part
    ]

    for part in parts:

        if part.isdigit():
            return part

    return None


# =============================================================================
# VIEW NAME
# =============================================================================

def get_view_name(path):
    """
    Safely resolve the Django URL name.
    """

    try:

        resolved = resolve(path)

        return (
            resolved.url_name
            or resolved.view_name
            or ""
        )

    except Exception:
        return ""


# =============================================================================
# USER NAME
# =============================================================================

def get_username(request):

    try:

        if request.user.is_authenticated:
            return request.user.username

    except Exception:
        pass

    return "System"


# =============================================================================
# CENTRAL AUDIT MIDDLEWARE
# =============================================================================

class AuditLogMiddleware:
    """
    Central audit middleware.

    Every successful POST/PUT/PATCH/DELETE request is recorded.

    Audit failures are intentionally swallowed so that an audit problem
    can never crash the actual application request.
    """

    def __init__(self, get_response):

        self.get_response = get_response

    def __call__(self, request):

        # ---------------------------------------------------------------------
        # Execute the actual application request first.
        # ---------------------------------------------------------------------

        response = self.get_response(request)

        # ---------------------------------------------------------------------
        # Never allow audit logging to break the application.
        # ---------------------------------------------------------------------

        try:

            path = request.path
            method = request.method.upper()

            # ---------------------------------------------------------------
            # Ignore static/media/debug requests.
            # ---------------------------------------------------------------

            if any(
                path.startswith(prefix)
                for prefix in IGNORED_PATH_PREFIXES
            ):
                return response

            # ---------------------------------------------------------------
            # Only successful requests.
            #
            # 400/401/403/404/500 etc. are not recorded as successful
            # business actions.
            # ---------------------------------------------------------------

            if response.status_code >= 400:
                return response

            # ---------------------------------------------------------------
            # Ignore normal GET page/API requests.
            # ---------------------------------------------------------------

            if method not in AUDITABLE_METHODS:
                return response

            # ---------------------------------------------------------------
            # Determine module.
            # ---------------------------------------------------------------

            category = get_category_from_path(
                path
            )

            # ---------------------------------------------------------------
            # Determine action.
            # ---------------------------------------------------------------

            action_type = get_action_type(
                method,
                path,
            )

            # ---------------------------------------------------------------
            # Determine object ID.
            # ---------------------------------------------------------------

            object_id = get_object_id_from_path(
                path
            )

            # ---------------------------------------------------------------
            # Determine Django view.
            # ---------------------------------------------------------------

            view_name = get_view_name(
                path
            )

            # ---------------------------------------------------------------
            # User.
            # ---------------------------------------------------------------

            username = get_username(
                request
            )

            # ---------------------------------------------------------------
            # Human-readable action.
            # ---------------------------------------------------------------

            action = get_action_description(
                method=method,
                path=path,
                action_type=action_type,
                category=category,
            )

            # ---------------------------------------------------------------
            # Additional details.
            # ---------------------------------------------------------------

            details_lines = [
                f"User: {username}",
                f"Method: {method}",
                f"Path: {path}",
            ]

            if view_name:
                details_lines.append(
                    f"View: {view_name}"
                )

            if object_id:
                details_lines.append(
                    f"Object ID: {object_id}"
                )

            details_lines.append(
                f"Status: {response.status_code}"
            )

            details = "\n".join(
                details_lines
            )

            # ---------------------------------------------------------------
            # Create audit record.
            # ---------------------------------------------------------------

            ActivityLog.objects.create(

                user=(
                    request.user
                    if request.user.is_authenticated
                    else None
                ),

                action=action,

                action_type=action_type,

                category=category,

                object_type="",

                object_id=object_id,

                details=details,
            )

        except Exception:
            """
            VERY IMPORTANT:

            Audit logging must never prevent the original request from
            succeeding.

            If something goes wrong here, simply return the original
            response.
            """

            pass

        return response
