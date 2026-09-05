"""
Middleware to enforce password change on first login.
"""
from django.shortcuts import redirect
from django.urls import resolve


class ForcePasswordChangeMiddleware:
    """
    Middleware that redirects users who must change their password
    to the password change page, except for the change page itself and logout.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # URLs that should be accessible even when password change is required
            allowed_urls = [
                "accounts:force_password_change",
                "logout",
                "login",
            ]
            try:
                resolved = resolve(request.path_info)
                # Build full namespaced URL name (e.g., "accounts:force_password_change")
                if resolved.namespace:
                    current_url_name = f"{resolved.namespace}:{resolved.url_name}"
                else:
                    current_url_name = resolved.url_name
            except Exception:
                current_url_name = None

            if (
                request.user.must_change_password
                and current_url_name not in allowed_urls
            ):
                return redirect("accounts:force_password_change")

        response = self.get_response(request)
        return response
