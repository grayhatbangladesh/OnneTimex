"""Ads views."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class AdsPlansView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"success": True, "data": [], "message": "", "meta": {"count": 0}})


class AdsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"success": True, "data": [], "message": "", "meta": {"count": 0}})

    def post(self, request):
        return Response({"success": True, "data": {"id": "ad_id"}, "message": "Ad created.", "meta": {}})


class AdsDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ad_id):
        return Response({"success": True, "data": {"id": ad_id}, "message": "", "meta": {}})

    def patch(self, request, ad_id):
        return Response({"success": True, "data": {"id": ad_id}, "message": "Updated.", "meta": {}})

    def delete(self, request, ad_id):
        return Response({"success": True, "data": {}, "message": "Deleted.", "meta": {}})


class AdsPayView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ad_id):
        return Response({"success": True, "data": {"id": ad_id, "status": "paid"}, "message": "Payment processed.", "meta": {}})


class AdsActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ad_id):
        action = request.data.get("action", "pause")
        return Response({"success": True, "data": {"id": ad_id, "status": action}, "message": f"Action {action}.", "meta": {}})


class AdsImpressionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ad_id):
        return Response({"success": True, "data": {"counted": True, "duration_seconds": 0}, "message": "Impression recorded.", "meta": {}})


class AdsAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ad_id):
        return Response({"success": True, "data": {"ad_id": ad_id}, "message": "", "meta": {}})


class AdsFeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"success": True, "data": [], "message": "", "meta": {"count": 0}})


class AdsCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({"success": True, "data": {"id": "ad_id"}, "message": "Ad created.", "meta": {}})
