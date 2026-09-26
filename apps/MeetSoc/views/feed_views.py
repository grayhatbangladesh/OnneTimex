import json
from datetime import timedelta

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetSoc.models import FeedHide, FeedSnooze, RecentSearch, SavedPost
from apps.MeetSoc.services.feed_services import FeedService
from apps.MeetSoc.models import Post, PostReaction
from apps.MeetSoc.serializers import FeedPostListSerializer
from apps.MeetSoc.views.posts_views import StoriesFeedView


class FeedView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FeedPostListSerializer

    def get(self, request):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        acting_as_page = getattr(request, "acting_as_page", None)

        seen_raw = request.query_params.get("seen_ids", "")
        seen_ids = set()
        if seen_raw:
            try:
                seen_ids = set(json.loads(seen_raw))
            except (json.JSONDecodeError, TypeError):
                pass

        if acting_as_page:
            offset = (page - 1) * page_size
            qs = Post.objects.filter(page_id=acting_as_page).select_related(
                "category", "author"
            ).prefetch_related("tags", "media_items").order_by("-created_at")
            total = qs.count()
            posts_page = qs[offset:offset + page_size]
            post_ids = [p.id for p in posts_page]
            user_reactions = PostReaction.objects.filter(
                post_id__in=post_ids, user=request.user
            ).values_list("post_id", "reaction_type")
            reaction_map = {str(pid): rtype for pid, rtype in user_reactions}
            for p in posts_page:
                p._user_reaction = reaction_map.get(str(p.id))
            serialized_posts = FeedPostListSerializer(
                posts_page, many=True, context={"request": request}
            ).data
            return Response({
                "success": True, "data": serialized_posts, "message": "",
                "meta": {"page": page, "total": total, "has_more": offset + page_size < total}
            })

        svc = FeedService(request.user)
        feed_items, total = svc.get_feed(page=page, page_size=page_size, seen_ids=seen_ids)

        post_ids = [item["id"] for item in feed_items if item.get("type") == "post"]
        ad_ids = [item["id"] for item in feed_items if item.get("type") == "ad"]

        posts = Post.objects.filter(id__in=post_ids).select_related(
            "category", "author"
        ).prefetch_related("tags", "media_items")
        post_map = {str(p.id): p for p in posts}
        post_order = {item["id"]: idx for idx, item in enumerate(feed_items) if item.get("type") == "post"}

        ordered_posts = sorted(posts, key=lambda p: post_order.get(str(p.id), 999))

        post_id_list = [p.id for p in ordered_posts]
        user_reactions = PostReaction.objects.filter(
            post_id__in=post_id_list, user=request.user
        ).values_list("post_id", "reaction_type")
        reaction_map = {str(pid): rtype for pid, rtype in user_reactions}
        for post in ordered_posts:
            post._user_reaction = reaction_map.get(str(post.id))

        serialized_posts = FeedPostListSerializer(
            ordered_posts, many=True, context={"request": request}
        ).data

        ad_items = [item for item in feed_items if item.get("type") == "ad"]

        combined = []
        post_idx = 0
        for item in feed_items:
            if item.get("type") == "post":
                if post_idx < len(serialized_posts):
                    combined.append(serialized_posts[post_idx])
                    post_idx += 1
            elif item.get("type") == "ad":
                combined.append({
                    "__ad__": True,
                    "id": item["id"],
                    "title": item.get("title", ""),
                    "message": item.get("message", ""),
                    "image": item.get("image"),
                    "cta_button": item.get("cta_button", "none"),
                    "content_type": item.get("content_type"),
                    "content_id": item.get("content_id"),
                    "advertiser_id": item.get("advertiser_id"),
                })

        return Response(
            {
                "success": True,
                "data": combined,
                "message": "",
                "meta": {
                    "page": page,
                    "total": total,
                    "has_more": page * page_size < total,
                },
            }
        )


class FeedStoriesView(StoriesFeedView):
    """Same as posts stories feed; exposed under /feed/stories/."""
    pass


class FeedHideView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def post(self, request, post_id):
        FeedHide.objects.get_or_create(user=request.user, post_id=post_id)
        FeedService(request.user).invalidate_feed_cache(str(request.user.id))
        return Response({"success": True, "data": {}, "message": "Hidden.", "meta": {}})


class FeedSnoozeView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def post(self, request, user_id):
        until = timezone.now() + timedelta(days=30)
        FeedSnooze.objects.update_or_create(
            user=request.user,
            snoozed_user_id=user_id,
            defaults={"until": until},
        )
        FeedService(request.user).invalidate_feed_cache(str(request.user.id))
        return Response({"success": True, "data": {}, "message": "Snoozed.", "meta": {}})


class SavedPostsView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FeedPostListSerializer

    def get(self, request):
        ids = SavedPost.objects.filter(user=request.user).values_list("post_id", flat=True)
        qs = Post.objects.filter(id__in=ids).order_by("-created_at")
        return Response(
            {
                "success": True,
                "data": FeedPostListSerializer(qs, many=True, context={"request": request}).data,
                "message": "",
                "meta": {},
            }
        )


class SavePostView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def post(self, request, post_id):
        SavedPost.objects.get_or_create(user=request.user, post_id=post_id)
        return Response({"success": True, "data": {}, "message": "Saved.", "meta": {}})

    def delete(self, request, post_id):
        SavedPost.objects.filter(user=request.user, post_id=post_id).delete()
        return Response({"success": True, "data": {}, "message": "Removed.", "meta": {}}, status=204)
