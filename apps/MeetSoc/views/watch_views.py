from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetSoc.models import ContentTag, Post
from apps.MeetSoc.models import WatchVideo, WatchVideoComment
from apps.MeetSoc.serializers import WatchVideoSerializer, WatchVideoCommentSerializer
from apps.MeetSoc.core.media_processing import optimize_image, optimize_video
from apps.MeetSoc.core.utils import sanitize_html


def _parse_tag_ids(data):
    raw = data.get("tag_ids")
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    if isinstance(raw, str):
        return [x.strip() for x in raw.split(",") if x.strip()]
    return []


class WatchListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WatchVideoSerializer

    def get(self, request):
        page = int(request.query_params.get("page", 1))
        limit = 20
        offset = (page - 1) * limit
        qs = WatchVideo.objects.select_related("category", "author__profile").prefetch_related("tags").exclude(is_on_hold=True).order_by(
            "-created_at"
        )
        total = qs.count()
        videos = qs[offset:offset + limit]
        return Response({
            "success": True,
            "data": WatchVideoSerializer(videos, many=True, context={"request": request}).data,
            "message": "",
            "meta": {"page": page, "total": total, "has_more": offset + limit < total},
        })

    def post(self, request):
        video = request.FILES.get("video_file")
        thumb = request.FILES.get("thumbnail")
        if not video:
            return Response(
                {"success": False, "error": {"code": "REQUIRED", "message": "video_file required.", "details": {}}},
                status=400,
            )
        cid = request.data.get("category_id")
        if cid in ("", None):
            cid = None
        v = WatchVideo.objects.create(
            author=request.user,
            title=request.data.get("title", ""),
            description=request.data.get("description", ""),
            video_file=optimize_video(video),
            thumbnail=optimize_image(thumb) if thumb else None,
            duration=float(request.data.get("duration", 0)),
            category_id=cid,
        )
        tids = _parse_tag_ids(request.data)
        if tids:
            v.tags.set(ContentTag.objects.filter(id__in=tids))
        return Response(
            {"success": True, "data": WatchVideoSerializer(v, context={"request": request}).data, "message": "Uploaded.", "meta": {}},
            status=201,
        )


class WatchDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WatchVideoSerializer

    def get(self, request, video_id):
        v = get_object_or_404(
            WatchVideo.objects.select_related("category", "author__profile").prefetch_related("tags"),
            pk=video_id,
        )
        if v.is_on_hold:
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Content unavailable.", "details": {}}}, status=403)
        from django.core.cache import cache

        from apps.recommendations.models import UserInteraction
        from apps.recommendations.services import InterestService, InteractionService

        v.views_count += 1
        v.save(update_fields=["views_count"])
        ck = f"rec:wclick:{request.user.id}:{video_id}"
        if not cache.get(ck):
            InteractionService.record_watch_video_event(
                request.user, v, UserInteraction.ACTION_CLICK
            )
            cache.set(ck, 1, 120)
            InterestService.refresh_profile_snapshot(request.user)
        return Response({
            "success": True,
            "data": WatchVideoSerializer(v, context={"request": request}).data,
            "message": "",
            "meta": {},
        })


class WatchVideoReactView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, video_id):
        video = get_object_or_404(WatchVideo, pk=video_id)
        from apps.MeetSoc.models import Reaction

        ct = ContentType.objects.get_for_model(WatchVideo)
        reaction_type = request.data.get("reaction_type", "like")
        existing = Reaction.objects.filter(user=request.user, content_type=ct, object_id=video.id).first()

        if existing:
            if existing.reaction_type == reaction_type:
                existing.delete()
                video.likes_count = max(0, video.likes_count - 1)
                video.save(update_fields=["likes_count"])
                return Response({"success": True, "data": {"reacted": False, "reaction_type": None, "likes_count": video.likes_count}, "message": "Unliked.", "meta": {}})
            else:
                existing.reaction_type = reaction_type
                existing.save(update_fields=["reaction_type"])
                return Response({"success": True, "data": {"reacted": True, "reaction_type": reaction_type, "likes_count": video.likes_count}, "message": "Reacted.", "meta": {}})
        else:
            Reaction.objects.create(user=request.user, reaction_type=reaction_type, content_type=ct, object_id=video.id)
            video.likes_count += 1
            video.save(update_fields=["likes_count"])
            return Response({"success": True, "data": {"reacted": True, "reaction_type": reaction_type, "likes_count": video.likes_count}, "message": "Liked.", "meta": {}}, status=201)


class WatchVideoCommentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, video_id):
        video = get_object_or_404(WatchVideo, pk=video_id)
        comments = WatchVideoComment.objects.filter(video=video).select_related("author", "author__profile").order_by("-created_at")[:100]
        return Response({
            "success": True,
            "data": WatchVideoCommentSerializer(comments, many=True, context={"request": request}).data,
            "message": "",
            "meta": {},
        })

    def post(self, request, video_id):
        video = get_object_or_404(WatchVideo, pk=video_id)
        content = sanitize_html(request.data.get("content", ""))
        if not content:
            return Response({"success": False, "error": {"code": "REQUIRED", "message": "content required.", "details": {}}}, status=400)
        comment = WatchVideoComment.objects.create(video=video, author=request.user, content=content)
        video.comments_count += 1
        video.save(update_fields=["comments_count"])

        if video.author_id != request.user.id:
            from apps.MeetSoc.tasks.notification_tasks import notify
            notify(
                recipient_id=video.author_id,
                actor_id=request.user.id,
                notification_type="post_comment",
                verb=f"{request.user.full_name or request.user.username} commented on your video",
                data={"video_id": str(video.id), "comment_id": str(comment.id)},
                target_type="watch_video",
                target_id=video.id,
            )

        return Response({
            "success": True,
            "data": WatchVideoCommentSerializer(comment, context={"request": request}).data,
            "message": "Commented.",
            "meta": {},
        }, status=201)


class WatchVideoShareView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, video_id):
        video = get_object_or_404(WatchVideo, pk=video_id)
        share = Post.objects.create(
            author=request.user,
            content=request.data.get("content", ""),
            post_type="shared",
            privacy=request.data.get("privacy", "public"),
        )
        video.shares_count += 1
        video.save(update_fields=["shares_count"])

        if video.author_id != request.user.id:
            from apps.MeetSoc.tasks.notification_tasks import notify
            notify(
                recipient_id=video.author_id,
                actor_id=request.user.id,
                notification_type="post_share",
                verb=f"{request.user.full_name or request.user.username} shared your video",
                data={"video_id": str(video.id), "shared_post_id": str(share.id)},
                target_type="watch_video",
                target_id=video.id,
            )

        return Response({"success": True, "data": {"shares_count": video.shares_count}, "message": "Shared.", "meta": {}}, status=201)
