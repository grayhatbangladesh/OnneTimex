"""
Wrap non-paginated DRF responses in MeetSoc success envelope.
Paginated responses are built by StandardPagination.
"""
from rest_framework.renderers import JSONRenderer


class MeetSocJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type, renderer_context):
        response = renderer_context.get("response")
        if response is not None and getattr(response, "exception", False):
            return super().render(data, accepted_media_type, renderer_context)
        if isinstance(data, dict) and data.get("success") is True:
            return super().render(data, accepted_media_type, renderer_context)
        if isinstance(data, dict) and "results" in data and "count" in data:
            return super().render(data, accepted_media_type, renderer_context)

        wrapped = {
            "success": True,
            "data": data,
            "message": "",
            "meta": {},
        }
        return super().render(wrapped, accepted_media_type, renderer_context)
