"""
Request ID middleware + Page Account middleware.
"""
import uuid

from django.core.exceptions import ValidationError
from django.utils.deprecation import MiddlewareMixin

from apps.MeetSoc.models import PageAdmin


class RequestIDMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.request_id = request.META.get("HTTP_X_REQUEST_ID", str(uuid.uuid4()))


class PageAccountMiddleware:
    """
    Check X-Acting-As header.
    If set, the user is acting as a page. Store the page ID on request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.acting_as_page = None
        acting_as = request.headers.get("X-Acting-As")
        if acting_as and request.user.is_authenticated:
            try:
                from uuid import UUID
                UUID(acting_as)  # validate UUID format
                if PageAdmin.objects.filter(page_id=acting_as, user=request.user).exists():
                    request.acting_as_page = acting_as
            except (ValueError, TypeError):
                # acting_as is not a UUID — try slug lookup
                from apps.MeetSoc.models import Page
                try:
                    page = Page.objects.get(slug=acting_as)
                    if PageAdmin.objects.filter(page=page, user=request.user).exists():
                        request.acting_as_page = str(page.id)
                except Page.DoesNotExist:
                    pass
            except ValidationError:
                pass  # Invalid user — silently ignore
        response = self.get_response(request)
        return response
