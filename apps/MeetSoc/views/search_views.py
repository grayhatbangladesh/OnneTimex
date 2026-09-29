from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetSoc.models import RecentSearch
from apps.MeetSoc.services.search_services import SearchService
from apps.MeetSoc.serializers import SearchResultSerializer, RecentSearchSerializer, TrendingSerializer


class UniversalSearchView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SearchResultSerializer

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        st = request.query_params.get("type", "all")
        # Record the search BEFORE running it so history is kept even if the
        # search itself fails.
        if q:
            try:
                RecentSearch.objects.create(user=request.user, query=q[:255])
            except Exception:
                pass
        svc = SearchService()
        data = svc.search(q, request.user, search_type=st)
        return Response({"success": True, "data": data, "message": "", "meta": {}})


class RecentSearchView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RecentSearchSerializer

    def get(self, request):
        qs = RecentSearch.objects.filter(user=request.user)[:20]
        return Response(
            {
                "success": True,
                "data": [{"query": r.query, "created_at": r.created_at.isoformat()} for r in qs],
                "message": "",
                "meta": {},
            }
        )

    def delete(self, request):
        RecentSearch.objects.filter(user=request.user).delete()
        return Response({"success": True, "data": {}, "message": "Cleared.", "meta": {}}, status=204)


class TrendingView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TrendingSerializer

    def get(self, request):
        try:
            conn = cache.client.get_client()
            tags = conn.zrevrange("trending:hashtags", 0, 9, withscores=True)
        except Exception:
            # LocMem/other caches expose no redis client — return an empty list.
            tags = []
        return Response({"success": True, "data": {"hashtags": tags}, "message": "", "meta": {}})
