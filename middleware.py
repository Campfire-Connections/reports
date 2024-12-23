# reports/middleware.py

from django.core.exceptions import PermissionDenied


class ReportAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Middleware logic to validate report access can be added here.
        return self.get_response(request)
