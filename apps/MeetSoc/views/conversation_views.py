"""Conversation views."""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"success": True, "data": [], "message": "", "meta": {"count": 0}})

    def post(self, request):
        return Response({"success": True, "data": {"id": str(request.user.id), "created": True}, "message": "Conversation created.", "meta": {}})


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        return Response({"success": True, "data": {"id": conversation_id}, "message": "", "meta": {}})

    def put(self, request, conversation_id):
        return Response({"success": True, "data": {"id": conversation_id}, "message": "Updated.", "meta": {}})

    def delete(self, request, conversation_id):
        return Response({"success": True, "data": {}, "message": "Deleted.", "meta": {}})


class ConversationMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        return Response({"success": True, "data": [], "message": "", "meta": {"count": 0}})

    def post(self, request, conversation_id):
        return Response({"success": True, "data": {"id": "msg_id"}, "message": "Message sent.", "meta": {}})


class ConversationDirectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({"success": True, "data": {"id": "conv_id", "created": True}, "message": "Direct conversation.", "meta": {}})


class OnlineStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ids = request.query_params.get("ids", "")
        return Response({"success": True, "data": {}, "message": "", "meta": {}})
