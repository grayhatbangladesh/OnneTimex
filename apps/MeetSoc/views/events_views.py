"""Events views."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class EventsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"success": True, "data": [], "message": "", "meta": {"count": 0}})

    def post(self, request):
        return Response({"success": True, "data": {"id": "event_id"}, "message": "Event created.", "meta": {}})


class EventsDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        return Response({"success": True, "data": {"id": event_id}, "message": "", "meta": {}})
