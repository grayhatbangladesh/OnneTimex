"""Category views."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class CategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"success": True, "data": [], "message": "", "meta": {"count": 0}})

    def post(self, request):
        return Response({"success": True, "data": {"id": "cat_id"}, "message": "Category created.", "meta": {}})


class TagListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"success": True, "data": [], "message": "", "meta": {"count": 0}})

    def post(self, request):
        return Response({"success": True, "data": {"id": "tag_id", "name": request.data.get("name", "")}, "message": "Tag created.", "meta": {}})
