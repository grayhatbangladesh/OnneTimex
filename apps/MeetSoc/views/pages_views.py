from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetSoc.models import Page, PageAdmin, PageFollower
from apps.MeetSoc.serializers import PageSerializer, PageAdminSerializer, PageFollowerSerializer
from apps.MeetSoc.models import Post, PostMedia
from apps.MeetSoc.serializers import PostDetailSerializer, PostListSerializer
from apps.MeetSoc.core.media_processing import optimize_media
from apps.MeetSoc.core.utils import sanitize_html


class PageListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PageSerializer

    def get(self, request):
        qs = Page.objects.all().exclude(is_on_hold=True).order_by("-created_at")[:100]
        data = PageSerializer(qs, many=True).data
        return Response({"success": True, "data": data, "message": "", "meta": {}})

    def post(self, request):
        if getattr(request, "acting_as_page", None):
            return Response({"success": False, "message": "Page accounts cannot create pages."}, status=403)
        name = request.data.get("name", "Page")
        slug = slugify(name)[:250]
        base = slug
        n = 0
        while Page.objects.filter(slug=slug).exists():
            n += 1
            slug = f"{base}-{n}"[:250]
        p = Page.objects.create(
            name=name,
            slug=slug,
            category=request.data.get("category", ""),
            description=request.data.get("description", ""),
            created_by=request.user,
        )
        avatar = request.FILES.get("avatar")
        if avatar:
            p.avatar = avatar
        cover = request.FILES.get("cover_photo")
        if cover:
            p.cover_photo = cover
        if avatar or cover:
            p.save()
        PageAdmin.objects.create(page=p, user=request.user, role="owner")
        return Response(
            {"success": True, "data": {"id": str(p.id), "slug": p.slug}, "message": "Created.", "meta": {}},
            status=201,
        )


class PageMyView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PageSerializer

    def get(self, request):
        ids = PageAdmin.objects.filter(user=request.user).values_list("page_id", flat=True)
        qs = Page.objects.filter(id__in=ids).exclude(is_on_hold=True).order_by("-created_at")[:100]
        data = PageSerializer(qs, many=True).data
        return Response({"success": True, "data": data, "message": "", "meta": {}})


class PageFollowedView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PageSerializer

    def get(self, request):
        page_ids = PageFollower.objects.filter(user=request.user, is_liked=True).values_list("page_id", flat=True)
        qs = Page.objects.filter(id__in=page_ids).exclude(is_on_hold=True).order_by("-created_at")[:100]
        data = PageSerializer(qs, many=True).data
        return Response({"success": True, "data": data, "message": "", "meta": {}})


class PageDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PageSerializer

    def get(self, request, slug):
        p = get_object_or_404(Page, slug=slug)
        if p.is_on_hold:
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Content unavailable.", "details": {}}}, status=403)
        return Response(
            {
                "success": True,
                "data": {
                    "id": str(p.id),
                    "name": p.name,
                    "slug": p.slug,
                    "description": p.description,
                    "avatar": p.avatar.url if p.avatar else "",
                    "cover_photo": p.cover_photo.url if p.cover_photo else "",
                    "category": p.category,
                    "website": p.website,
                    "email": p.email,
                    "phone": p.phone,
                    "address": p.address,
                    "verified": p.verified,
                    "followers_count": p.followers_count,
                    "likes_count": p.likes_count,
                    "created_by": str(p.created_by_id),
                },
                "message": "",
                "meta": {},
            }
        )

    def put(self, request, slug):
        p = get_object_or_404(Page, slug=slug)
        if not PageAdmin.objects.filter(page=p, user=request.user, role__in=["owner", "admin", "editor"]).exists():
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Admin only.", "details": {}}}, status=403)
        p.name = request.data.get("name", p.name)
        p.description = request.data.get("description", p.description)
        if "cover_photo" in request.FILES:
            p.cover_photo = request.FILES["cover_photo"]
        if "avatar" in request.FILES:
            p.avatar = request.FILES["avatar"]
        p.save()
        return Response({"success": True, "data": {}, "message": "Updated.", "meta": {}})

    def delete(self, request, slug):
        p = get_object_or_404(Page, slug=slug)
        if p.created_by_id != request.user.id:
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Only the page creator can delete.", "details": {}}}, status=403)
        p.delete()
        return Response({"success": True, "data": {}, "message": "Deleted.", "meta": {}})


class PageLikeView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def post(self, request, slug):
        p = get_object_or_404(Page, slug=slug)
        PageFollower.objects.update_or_create(page=p, user=request.user, defaults={"is_liked": True})
        p.likes_count = PageFollower.objects.filter(page=p, is_liked=True).count()
        p.save(update_fields=["likes_count"])
        return Response({"success": True, "data": {}, "message": "Liked.", "meta": {}})


class PageFollowView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PageFollowerSerializer

    def post(self, request, slug):
        p = get_object_or_404(Page, slug=slug)
        _, created = PageFollower.objects.get_or_create(page=p, user=request.user, defaults={"is_liked": True})
        if not created:
            PageFollower.objects.filter(page=p, user=request.user).update(is_liked=True)
        p.followers_count = PageFollower.objects.filter(page=p, is_liked=True).count()
        p.likes_count = PageFollower.objects.filter(page=p, is_liked=True).count()
        p.save(update_fields=["followers_count", "likes_count"])
        if created and p.created_by_id != request.user.id:
            from apps.MeetSoc.tasks.notification_tasks import notify
            notify(
                recipient_id=p.created_by_id,
                actor_id=request.user.id,
                notification_type="follow",
                verb=f"{request.user.full_name or request.user.username} started following {p.name}",
                data={"page_id": str(p.id), "page_slug": p.slug},
                target_type="page",
                target_id=p.id,
            )
        return Response({"success": True, "data": {}, "message": "Followed.", "meta": {}})


class PageUnfollowView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def delete(self, request, slug):
        p = get_object_or_404(Page, slug=slug)
        PageFollower.objects.filter(page=p, user=request.user).delete()
        return Response({"success": True, "data": {}, "message": "Unfollowed.", "meta": {}}, status=204)


class PagePostsView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PostListSerializer

    def get(self, request, slug):
        p = get_object_or_404(Page, slug=slug)
        qs = Post.objects.filter(page=p).exclude(is_on_hold=True).order_by("-created_at")[:50]
        return Response(
            {
                "success": True,
                "data": PostListSerializer(qs, many=True, context={"request": request}).data,
                "message": "",
                "meta": {},
            }
        )

    def post(self, request, slug):
        p = get_object_or_404(Page, slug=slug)
        if not PageAdmin.objects.filter(page=p, user=request.user, role__in=["owner", "admin", "editor"]).exists():
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Editor only.", "details": {}}}, status=403)
        post = Post.objects.create(
            author=request.user,
            content=sanitize_html(request.data.get("content", "")),
            post_type=request.data.get("post_type", "text"),
            privacy="public",
            page=p,
        )
        # Same upload handling as POST /meetsoc/posts/ so page media actually saves.
        for i, f in enumerate(request.FILES.getlist("files")):
            mt = "video" if (f.content_type and f.content_type.startswith("video")) else "image"
            PostMedia.objects.create(
                post=post,
                file=optimize_media(f),
                media_type=mt,
                order=i,
            )
        return Response(
            {
                "success": True,
                "data": PostDetailSerializer(post, context={"request": request}).data,
                "message": "Posted.",
                "meta": {},
            },
            status=201,
        )


class PageFollowersView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PageFollowerSerializer

    def get(self, request, slug):
        p = get_object_or_404(Page, slug=slug)
        qs = PageFollower.objects.filter(page=p)
        from apps.accounts.serializers import UserPublicSerializer

        users = [f.user for f in qs]
        return Response(
            {
                "success": True,
                "data": UserPublicSerializer(users, many=True, context={"request": request}).data,
                "message": "",
                "meta": {},
            }
        )


class PageAdminsView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PageAdminSerializer

    def post(self, request, slug):
        p = get_object_or_404(Page, slug=slug)
        if not PageAdmin.objects.filter(page=p, user=request.user, role="owner").exists():
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Owner only.", "details": {}}}, status=403)
        uid = request.data.get("user_id")
        role = request.data.get("role", "editor")
        from django.contrib.auth import get_user_model

        u = get_object_or_404(get_user_model(), pk=uid)
        PageAdmin.objects.get_or_create(page=p, user=u, defaults={"role": role})
        return Response({"success": True, "data": {}, "message": "Admin added.", "meta": {}})


class PageInsightsView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def get(self, request, slug):
        p = get_object_or_404(Page, slug=slug)
        if not PageAdmin.objects.filter(page=p, user=request.user, role__in=["owner", "admin", "analyst"]).exists():
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Admin/analyst only.", "details": {}}}, status=403)
        return Response(
            {
                "success": True,
                "data": {
                    "followers": p.followers_count,
                    "likes": p.likes_count,
                    "posts": Post.objects.filter(page=p).count(),
                },
                "message": "",
                "meta": {},
            }
        )


class PageAccountSwitchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        admin_pages = PageAdmin.objects.filter(user=request.user).select_related("page")
        data = []
        for pa in admin_pages:
            p = pa.page
            if p.is_on_hold:
                continue
            data.append({
                "id": str(p.id),
                "name": p.name,
                "slug": p.slug,
                "avatar": p.avatar.url if p.avatar else "",
                "allowed_features": p.allowed_features,
                "role": pa.role,
            })
        return Response({"success": True, "data": data, "message": "", "meta": {}})
