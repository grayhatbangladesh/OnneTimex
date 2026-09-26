from django.contrib.contenttypes.models import ContentType
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetSoc.models import Comment
from apps.MeetSoc.models import Memory
from apps.MeetSoc.serializers import MemorySerializer
from apps.MeetSoc.models import Post, PostView
from apps.MeetSoc.models import Reaction


class MemoriesListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Memory.objects.filter(user=request.user).order_by("-year")[:50]
        data = [
            {
                "id": str(m.id),
                "year": m.year,
                "summary": m.summary,
                "post_id": str(m.post_id) if m.post_id else None,
            }
            for m in qs
        ]
        return Response({"success": True, "data": data, "message": "", "meta": {}})


class UserActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        seen = set()
        activities = []

        post_ct = ContentType.objects.get_for_model(Post)

        views_qs = PostView.objects.filter(viewer=user).select_related("post").order_by("-viewed_at")[:100]
        for v in views_qs:
            pid = str(v.post_id)
            if pid in seen:
                continue
            seen.add(pid)
            activities.append({
                "post_id": pid,
                "post_content": v.post.content[:200] if v.post.content else "",
                "activity_type": "viewed",
                "activity_time": v.viewed_at.isoformat(),
            })

        reactions_qs = (
            Reaction.objects.filter(user=user, content_type=post_ct)
            .select_related("content_object")
            .order_by("-created_at")[:100]
        )
        for r in reactions_qs:
            pid = str(r.object_id)
            if pid in seen:
                continue
            seen.add(pid)
            activities.append({
                "post_id": pid,
                "post_content": r.content_object.content[:200] if r.content_object and r.content_object.content else "",
                "activity_type": f"reacted ({r.reaction_type})",
                "activity_time": r.created_at.isoformat(),
            })

        comments_qs = (
            Comment.objects.filter(author=user)
            .select_related("post")
            .order_by("-created_at")[:100]
        )
        for c in comments_qs:
            pid = str(c.post_id)
            if pid in seen:
                continue
            seen.add(pid)
            activities.append({
                "post_id": pid,
                "post_content": c.post.content[:200] if c.post and c.post.content else "",
                "activity_type": "commented",
                "activity_time": c.created_at.isoformat(),
            })

        activities.sort(key=lambda x: x["activity_time"], reverse=True)

        return Response({
            "success": True,
            "data": activities[:100],
            "message": "",
            "meta": {},
        })
