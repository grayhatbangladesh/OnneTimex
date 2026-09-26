from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetSoc.services.feed_services import FeedService
from apps.MeetSoc.models import ContentTag, Friendship, Post, PostMedia, PostReaction, Story, StoryComment, StoryReaction, StoryView
from apps.MeetSoc.serializers import PostDetailSerializer, PostListSerializer, StoryCommentSerializer, StorySerializer
from apps.MeetSoc.core.media_processing import optimize_media
from apps.MeetSoc.core.utils import check_rate_limit, sanitize_html


def _post_rate_limit(user):
    return check_rate_limit(str(user.id), "post_create", settings.RATELIMIT_POSTS_PER_HOUR, 3600)


def _parse_tag_ids(data):
    raw = data.get("tag_ids")
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    if isinstance(raw, str):
        return [x.strip() for x in raw.split(",") if x.strip()]
    return []


class PostListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PostListSerializer

    def get(self, request):
        qs = Post.objects.filter(
            Q(author=request.user) | Q(privacy="public")
        ).exclude(author__status="banned").order_by("-created_at")[:50]
        return Response(
            {
                "success": True,
                "data": PostListSerializer(qs, many=True, context={"request": request}).data,
                "message": "",
                "meta": {},
            }
        )

    def post(self, request):
        if not _post_rate_limit(request.user):
            return Response(
                {"success": False, "error": {"code": "RATE_LIMIT", "message": "Post limit reached.", "details": {}}},
                status=429,
            )
        content = sanitize_html(request.data.get("content", ""))
        post_type = request.data.get("post_type", "text")
        privacy = request.data.get("privacy", "public")
        cid = request.data.get("category_id")
        if cid in ("", None):
            cid = None

        # Auto-set page_id from X-Acting-As header
        page_id = request.data.get("page_id")
        acting_as_page = getattr(request, "acting_as_page", None)
        if acting_as_page:
            page_id = acting_as_page
            privacy = "public"  # Page posts are always public

        post = Post.objects.create(
            author=request.user,
            content=content,
            post_type=post_type,
            privacy=privacy,
            feeling=request.data.get("feeling"),
            location=request.data.get("location"),
            link_preview=request.data.get("link_preview"),
            shared_post_id=request.data.get("shared_post_id"),
            group_id=request.data.get("group_id"),
            page_id=page_id,
            category_id=cid,
            is_anonymous=bool(request.data.get("is_anonymous", False)),
        )
        tag_ids = _parse_tag_ids(request.data)
        if tag_ids:
            post.tags.set(ContentTag.objects.filter(id__in=tag_ids))
        request.user.profile.posts_count = Post.objects.filter(author=request.user).count()
        request.user.profile.save(update_fields=["posts_count"])
        files = request.FILES.getlist("files")
        for i, f in enumerate(files):
            mt = "image"
            if f.content_type and f.content_type.startswith("video"):
                mt = "video"
            optimized_file = optimize_media(f)
            PostMedia.objects.create(
                post=post,
                file=optimized_file,
                media_type=mt,
                order=i,
            )
        
        # Clear feed cache for all users so they see the new post
        from apps.accounts.models import User
        for user_id in User.objects.values_list('id', flat=True):
            for page_num in range(1, 100):
                cache.delete(f'feed:{user_id}:{page_num}')
        
        return Response(
            {
                "success": True,
                "data": PostDetailSerializer(post, context={"request": request}).data,
                "message": "Post created.",
                "meta": {},
            },
            status=201,
        )


class PostDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PostDetailSerializer

    def get(self, request, post_id):
        post = get_object_or_404(
            Post.objects.select_related("category", "author").prefetch_related("tags", "media_items"),
            pk=post_id,
        )
        if post.is_on_hold:
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Content unavailable.", "details": {}}}, status=403)
        from apps.recommendations.services import InterestService, InteractionService

        ck = f"rec:click:{request.user.id}:{post_id}"
        if not cache.get(ck):
            InteractionService.record_post_click(request.user, post)
            cache.set(ck, 1, 120)
            InterestService.refresh_profile_snapshot(request.user)
        return Response(
            {
                "success": True,
                "data": PostDetailSerializer(post, context={"request": request}).data,
                "message": "",
                "meta": {},
            }
        )

    def put(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id, author=request.user)
        post.content = sanitize_html(request.data.get("content", post.content))
        post.privacy = request.data.get("privacy", post.privacy)
        post.is_edited = True
        post.save()
        
        # Clear feed cache
        from apps.accounts.models import User
        for user_id in User.objects.values_list('id', flat=True):
            for page_num in range(1, 100):
                cache.delete(f'feed:{user_id}:{page_num}')
        
        return Response(
            {
                "success": True,
                "data": PostDetailSerializer(post, context={"request": request}).data,
                "message": "Updated.",
                "meta": {},
            }
        )

    def delete(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id, author=request.user)
        post.delete()
        
        # Clear feed cache
        from apps.accounts.models import User
        for user_id in User.objects.values_list('id', flat=True):
            for page_num in range(1, 100):
                cache.delete(f'feed:{user_id}:{page_num}')
        
        return Response({"success": True, "data": {}, "message": "Deleted.", "meta": {}}, status=204)


class PostShareView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PostDetailSerializer

    def post(self, request, post_id):
        original = get_object_or_404(Post, pk=post_id)
        share = Post.objects.create(
            author=request.user,
            content=request.data.get("content", ""),
            post_type="shared",
            privacy=request.data.get("privacy", "public"),
            shared_post=original,
        )
        from apps.recommendations.services import InterestService, InteractionService

        InteractionService.record_post_share(request.user, original)
        InterestService.refresh_profile_snapshot(request.user)
        original.shares_count += 1
        original.save(update_fields=["shares_count"])

        if original.author_id != request.user.id:
            from apps.MeetSoc.tasks.notification_tasks import notify
            notify(
                recipient_id=original.author_id,
                actor_id=request.user.id,
                notification_type="post_share",
                verb=f"{request.user.full_name or request.user.username} shared your post",
                data={"post_id": str(original.id), "shared_post_id": str(share.id)},
                target_type="post",
                target_id=original.id,
            )

        return Response(
            {
                "success": True,
                "data": PostDetailSerializer(share, context={"request": request}).data,
                "message": "Shared.",
                "meta": {},
            },
            status=201,
        )


class PostSharesListView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PostListSerializer

    def get(self, request, post_id):
        qs = Post.objects.filter(shared_post_id=post_id).exclude(is_on_hold=True).order_by("-created_at")[:50]
        return Response(
            {
                "success": True,
                "data": PostListSerializer(qs, many=True, context={"request": request}).data,
                "message": "",
                "meta": {},
            }
        )


class PostViewRegisterView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        from apps.MeetSoc.models import PostView as PV

        _pv, created = PV.objects.get_or_create(post=post, viewer=request.user)
        post.views_count = PV.objects.filter(post=post).count()
        post.save(update_fields=["views_count"])
        watch_seconds = float(request.data.get("watch_seconds") or 0)
        from apps.recommendations.services import InterestService, InteractionService

        # First unique view: log interaction; further watch time should use POST /recommendations/track/
        if created:
            InteractionService.record_post_view(request.user, post, watch_seconds=watch_seconds)
            InterestService.refresh_profile_snapshot(request.user)
        return Response({"success": True, "data": {}, "message": "View recorded.", "meta": {}})


class StoriesFeedView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StorySerializer

    def get(self, request):
        friend_ids = Friendship.objects.filter(
            Q(sender=request.user, status="accepted") | Q(receiver=request.user, status="accepted")
        )
        ids = set()
        for f in friend_ids:
            ids.add(f.sender_id if f.receiver_id == request.user.id else f.receiver_id)
        ids.add(request.user.id)
        now = timezone.now()
        qs = Story.objects.filter(author_id__in=ids, expires_at__gt=now).order_by("-created_at")[:100]
        return Response(
            {
                "success": True,
                "data": StorySerializer(qs, many=True, context={"request": request}).data,
                "message": "",
                "meta": {},
            }
        )

    def post(self, request):
        expires = timezone.now() + timedelta(hours=24)
        s = Story.objects.create(
            author=request.user,
            media=optimize_media(request.FILES.get("media")) if request.FILES.get("media") else None,
            media_type=request.data.get("media_type", "image"),
            text_content=request.data.get("text_content"),
            background_color=request.data.get("background_color"),
            stickers=request.data.get("stickers"),
            music=request.data.get("music"),
            privacy=request.data.get("privacy", "friends"),
            expires_at=expires,
        )
        return Response(
            {
                "success": True,
                "data": StorySerializer(s, context={"request": request}).data,
                "message": "Story created.",
                "meta": {},
            },
            status=201,
        )


class StoryDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StorySerializer

    def delete(self, request, story_id):
        story = get_object_or_404(Story, pk=story_id, author=request.user)
        story.delete()
        return Response({"success": True, "data": {}, "message": "Deleted.", "meta": {}}, status=204)


class StoryViewView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def post(self, request, story_id):
        story = get_object_or_404(Story, pk=story_id)
        StoryView.objects.get_or_create(story=story, viewer=request.user)
        story.views_count = StoryView.objects.filter(story=story).count()
        story.save(update_fields=["views_count"])
        return Response({"success": True, "data": {}, "message": "Viewed.", "meta": {}})


class StoryViewersView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def get(self, request, story_id):
        story = get_object_or_404(Story, pk=story_id)
        if story.author_id != request.user.id:
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Only author.", "details": {}}}, status=403)
        views = StoryView.objects.filter(story=story).select_related("viewer")[:500]
        from apps.accounts.serializers import UserPublicSerializer

        users = [v.viewer for v in views]
        return Response(
            {
                "success": True,
                "data": UserPublicSerializer(users, many=True, context={"request": request}).data,
                "message": "",
                "meta": {},
            }
        )


class StoryArchiveView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StorySerializer

    def get(self, request):
        qs = Story.objects.filter(author=request.user).order_by("-created_at")[:200]
        return Response(
            {
                "success": True,
                "data": StorySerializer(qs, many=True, context={"request": request}).data,
                "message": "",
                "meta": {},
            }
        )


class StoryCommentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, story_id):
        story = get_object_or_404(Story, pk=story_id)
        comments = StoryComment.objects.filter(story=story, parent=None).order_by("-created_at")
        page = request.GET.get("page", 1)
        paginator = Paginator(comments, 20)
        try:
            page_obj = paginator.page(page)
        except Exception:
            return Response({"success": False, "data": [], "message": "Invalid page."}, status=400)
        return Response({
            "success": True,
            "data": StoryCommentSerializer(page_obj.object_list, many=True, context={"request": request}).data,
            "message": "",
            "meta": {"page": page, "pages": paginator.num_pages},
        })

    def post(self, request, story_id):
        story = get_object_or_404(Story, pk=story_id)
        content = request.data.get("content", "").strip()
        if not content:
            return Response({"success": False, "message": "Content is required."}, status=400)
        comment = StoryComment.objects.create(
            story=story,
            author=request.user,
            content=content,
            parent_id=request.data.get("parent_id"),
        )
        story.comments_count = StoryComment.objects.filter(story=story).count()
        story.save(update_fields=["comments_count"])
        return Response({
            "success": True,
            "data": StoryCommentSerializer(comment, context={"request": request}).data,
            "message": "Comment posted.",
        }, status=201)


class StoryReactView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, story_id):
        story = get_object_or_404(Story, pk=story_id)
        reaction_type = request.data.get("type", "love")
        existing = StoryReaction.objects.filter(story=story, user=request.user).first()
        if existing:
            existing.reaction_type = reaction_type
            existing.save(update_fields=["reaction_type"])
        else:
            StoryReaction.objects.create(story=story, user=request.user, reaction_type=reaction_type)
        story.reactions_count = StoryReaction.objects.filter(story=story).count()
        story.save(update_fields=["reactions_count"])
        return Response({"success": True, "data": {"reactions_count": story.reactions_count}, "message": ""})

    def delete(self, request, story_id):
        story = get_object_or_404(Story, pk=story_id)
        deleted, _ = StoryReaction.objects.filter(story=story, user=request.user).delete()
        if deleted:
            story.reactions_count = StoryReaction.objects.filter(story=story).count()
            story.save(update_fields=["reactions_count"])
        return Response({"success": True, "data": {"reactions_count": story.reactions_count}, "message": ""})


def _recalc_reactions_count(post):
    from django.db.models import Count
    counts = PostReaction.objects.filter(post=post).values("reaction_type").annotate(c=Count("id"))
    post.reactions_count = {r["reaction_type"]: r["c"] for r in counts}
    post.save(update_fields=["reactions_count"])


class PostReactView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        reaction_type = request.data.get("reaction_type", "like")
        reaction, created = PostReaction.objects.get_or_create(
            post=post, user=request.user, defaults={"reaction_type": reaction_type}
        )
        if not created and reaction.reaction_type != reaction_type:
            reaction.reaction_type = reaction_type
            reaction.save(update_fields=["reaction_type"])
        _recalc_reactions_count(post)

        if created and post.author_id != request.user.id:
            from apps.MeetSoc.tasks.notification_tasks import notify
            notify(
                recipient_id=post.author_id,
                actor_id=request.user.id,
                notification_type="post_like",
                verb=f"{request.user.full_name or request.user.username} reacted {reaction_type} to your post",
                data={"post_id": str(post.id)},
                target_type="post",
                target_id=post.id,
            )

        return Response(
            {
                "success": True,
                "data": {"id": str(reaction.id), "reaction_type": reaction.reaction_type},
                "message": "Reacted." if created else "Reaction updated.",
                "meta": {},
            },
            status=201 if created else 200,
        )

    def delete(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        deleted, _ = PostReaction.objects.filter(post=post, user=request.user).delete()
        _recalc_reactions_count(post)
        return Response(
            {
                "success": True,
                "data": {},
                "message": "Reaction removed." if deleted else "No reaction to remove.",
                "meta": {},
            }
        )


class PostReactionsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        reactions = PostReaction.objects.filter(post=post).select_related("user", "user__profile")[:100]
        from apps.accounts.serializers import UserPublicLiteSerializer
        data = [
            {
                "id": str(r.id),
                "user": UserPublicLiteSerializer(r.user, context={"request": request}).data,
                "reaction_type": r.reaction_type,
                "created_at": r.created_at.isoformat(),
            }
            for r in reactions
        ]
        return Response(
            {
                "success": True,
                "data": data,
                "message": "",
                "meta": {},
            }
        )
