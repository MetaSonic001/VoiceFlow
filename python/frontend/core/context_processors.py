from django.conf import settings


def global_context(request):
    """Context variables available to every template."""
    return {
        "BACKEND_API_URL": settings.BACKEND_API_URL,
        "tenant_id": getattr(request, "tenant_id", ""),
        "user_id": str(request.user.id) if request.user.is_authenticated else "",
    }
