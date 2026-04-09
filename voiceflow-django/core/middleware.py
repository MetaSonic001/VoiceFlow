class TenantMiddleware:
    """Injects tenant_id from the authenticated user into the request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant_id = ""
        if hasattr(request, "user") and request.user.is_authenticated:
            request.tenant_id = request.user.tenant_id or ""
        return self.get_response(request)
