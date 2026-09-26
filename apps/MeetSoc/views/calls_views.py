"""Calls views."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class CallsInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({"success": True, "data": {"call_id": "call_id"}, "message": "Call initiated.", "meta": {}})


class CallsAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, call_id):
        return Response({"success": True, "data": {"call_id": call_id}, "message": "Call accepted.", "meta": {}})


class CallsDeclineView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, call_id):
        return Response({"success": True, "data": {"call_id": call_id}, "message": "Call declined.", "meta": {}})


class CallsEndView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, call_id):
        return Response({"success": True, "data": {"call_id": call_id}, "message": "Call ended.", "meta": {}})


class CallsHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"success": True, "data": [], "message": "", "meta": {"count": 0}})


class CallsIceServersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"success": True, "data": {"iceServers": []}, "message": "", "meta": {}})
