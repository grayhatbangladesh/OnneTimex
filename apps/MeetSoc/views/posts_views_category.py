from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetSoc.models import ContentCategory, ContentTag


class CategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cats = ContentCategory.objects.filter(is_active=True).order_by("sort_order", "name")
        data = [{"id": str(c.id), "name": c.name, "slug": c.slug} for c in cats]
        return Response({"success": True, "data": data, "message": "", "meta": {}})


class TagListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        qs = ContentTag.objects.all()
        if q:
            qs = qs.filter(name__icontains=q)[:20]
        else:
            qs = qs.order_by("name")[:50]
        data = [{"id": str(t.id), "name": t.name, "slug": t.slug} for t in qs]
        return Response({"success": True, "data": data, "message": "", "meta": {}})

    def post(self, request):
        name = request.data.get("name", "").strip()
        if not name:
            return Response({"success": False, "message": "Name required."}, status=400)
        tag, _ = ContentTag.objects.get_or_create(name__iexact=name, defaults={"name": name})
        return Response(
            {"success": True, "data": {"id": str(tag.id), "name": tag.name, "slug": tag.slug}, "message": "", "meta": {}},
            status=201,
        )
