from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetSoc.models import Group, GroupInvite, GroupMembership
from apps.MeetSoc.serializers import GroupSerializer, GroupMembershipSerializer, GroupInviteSerializer
from apps.MeetSoc.models import Post
from apps.MeetSoc.serializers import PostListSerializer
from apps.MeetSoc.core.utils import sanitize_html


class GroupListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerializer

    def get(self, request):
        my_group_ids = list(
            GroupMembership.objects.filter(user=request.user, status="active").values_list("group_id", flat=True)
        )
        my_pending_ids = set(
            GroupMembership.objects.filter(user=request.user, status="pending").values_list("group_id", flat=True)
        )
        public_qs = Group.objects.filter(privacy="public").exclude(is_on_hold=True).order_by("-created_at")[:100]
        member_qs = Group.objects.filter(id__in=my_group_ids).exclude(is_on_hold=True)
        all_groups = list(public_qs) + [g for g in member_qs if g not in public_qs]
        my_ids = set(my_group_ids)
        data = []
        for g in all_groups:
            data.append({
                "id": str(g.id),
                "name": g.name,
                "slug": g.slug,
                "description": g.description,
                "cover_photo": g.cover_photo.url if g.cover_photo else "",
                "avatar": g.avatar.url if g.avatar else "",
                "privacy": g.privacy,
                "category": g.category,
                "members_count": g.members_count,
                "posts_count": g.posts_count,
                "created_by": str(g.created_by_id),
                "is_member": str(g.id) in my_ids,
                "is_pending": str(g.id) in my_pending_ids,
            })
        return Response({"success": True, "data": data, "message": "", "meta": {}})

    def post(self, request):
        if getattr(request, "acting_as_page", None):
            return Response({"success": False, "message": "Page accounts cannot create groups."}, status=403)
        name = request.data.get("name", "Group")
        slug = slugify(name)[:250]
        base = slug
        n = 0
        while Group.objects.filter(slug=slug).exists():
            n += 1
            slug = f"{base}-{n}"[:250]
        g = Group.objects.create(
            name=name,
            slug=slug,
            description=request.data.get("description", ""),
            privacy=request.data.get("privacy", "public"),
            category=request.data.get("category", ""),
            cover_photo=request.FILES.get("cover_photo"),
            avatar=request.FILES.get("avatar"),
            created_by=request.user,
        )
        GroupMembership.objects.create(group=g, user=request.user, role="admin", status="active")
        g.members_count = 1
        g.save(update_fields=["members_count"])
        return Response(
            {"success": True, "data": {"id": str(g.id), "slug": g.slug}, "message": "Created.", "meta": {}},
            status=201,
        )


class GroupMyView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerializer

    def get(self, request):
        ids = GroupMembership.objects.filter(user=request.user, status="active").values_list("group_id", flat=True)
        qs = Group.objects.filter(id__in=ids).exclude(is_on_hold=True)
        data = []
        for g in qs:
            data.append({
                "id": str(g.id),
                "name": g.name,
                "slug": g.slug,
                "description": g.description,
                "cover_photo": g.cover_photo.url if g.cover_photo else "",
                "avatar": g.avatar.url if g.avatar else "",
                "privacy": g.privacy,
                "category": g.category,
                "members_count": g.members_count,
                "posts_count": g.posts_count,
                "created_by": str(g.created_by_id),
                "is_member": True,
            })
        return Response({"success": True, "data": data, "message": "", "meta": {}})


class GroupDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerializer

    def get(self, request, slug):
        g = get_object_or_404(Group, slug=slug)
        if g.is_on_hold:
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Content unavailable.", "details": {}}}, status=403)
        return Response(
            {
                "success": True,
                "data": {
                    "id": str(g.id),
                    "name": g.name,
                    "slug": g.slug,
                    "description": g.description,
                    "cover_photo": g.cover_photo.url if g.cover_photo else "",
                    "avatar": g.avatar.url if g.avatar else "",
                    "privacy": g.privacy,
                    "category": g.category,
                    "rules": g.rules,
                    "members_count": g.members_count,
                    "posts_count": g.posts_count,
                    "created_by": str(g.created_by_id),
                },
                "message": "",
                "meta": {},
            }
        )

    def put(self, request, slug):
        g = get_object_or_404(Group, slug=slug)
        if not GroupMembership.objects.filter(group=g, user=request.user, role="admin", status="active").exists():
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Admin only.", "details": {}}}, status=403)
        g.name = request.data.get("name", g.name)
        g.description = request.data.get("description", g.description)
        g.privacy = request.data.get("privacy", g.privacy)
        g.category = request.data.get("category", g.category)
        if "cover_photo" in request.FILES:
            g.cover_photo = request.FILES["cover_photo"]
        if "avatar" in request.FILES:
            g.avatar = request.FILES["avatar"]
        g.save()
        return Response({"success": True, "data": {"slug": g.slug}, "message": "Updated.", "meta": {}})

    def delete(self, request, slug):
        g = get_object_or_404(Group, slug=slug)
        if not GroupMembership.objects.filter(group=g, user=request.user, role="admin", status="active").exists():
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Admin only.", "details": {}}}, status=403)
        g.delete()
        return Response({"success": True, "data": {}, "message": "Deleted.", "meta": {}}, status=204)


class GroupJoinView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerializer

    def post(self, request, slug):
        g = get_object_or_404(Group, slug=slug)
        status_val = "active" if g.privacy == "public" else "pending"
        _, created = GroupMembership.objects.get_or_create(
            group=g,
            user=request.user,
            defaults={"role": "member", "status": status_val},
        )
        if created and g.created_by_id != request.user.id:
            from apps.MeetSoc.tasks.notification_tasks import notify
            verb_suffix = "wants to join" if status_val == "pending" else "joined"
            notify(
                recipient_id=g.created_by_id,
                actor_id=request.user.id,
                notification_type="group_invite",
                verb=f"{request.user.full_name or request.user.username} {verb_suffix} {g.name}",
                data={"group_id": str(g.id), "group_slug": g.slug},
                target_type="group",
                target_id=g.id,
            )
        return Response({"success": True, "data": {}, "message": "Joined.", "meta": {}})


class GroupLeaveView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def post(self, request, slug):
        g = get_object_or_404(Group, slug=slug)
        GroupMembership.objects.filter(group=g, user=request.user).delete()
        return Response({"success": True, "data": {}, "message": "Left.", "meta": {}})


class GroupMembersView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupMembershipSerializer

    def get(self, request, slug):
        g = get_object_or_404(Group, slug=slug)
        qs = GroupMembership.objects.filter(group=g, status="active")
        from apps.accounts.serializers import UserPublicSerializer

        users = [m.user for m in qs]
        return Response(
            {
                "success": True,
                "data": UserPublicSerializer(users, many=True, context={"request": request}).data,
                "message": "",
                "meta": {},
            }
        )


class GroupInviteView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupInviteSerializer

    def post(self, request, slug):
        g = get_object_or_404(Group, slug=slug)
        uid = request.data.get("user_id")
        from django.contrib.auth import get_user_model

        u = get_object_or_404(get_user_model(), pk=uid)
        GroupInvite.objects.get_or_create(
            group=g,
            invited_by=request.user,
            invited_user=u,
            defaults={"status": "pending"},
        )
        return Response({"success": True, "data": {}, "message": "Invited.", "meta": {}})


class GroupMemberRoleView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupMembershipSerializer

    def patch(self, request, slug, uid):
        g = get_object_or_404(Group, slug=slug)
        if not GroupMembership.objects.filter(group=g, user=request.user, role="admin", status="active").exists():
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Admin only.", "details": {}}}, status=403)
        m = get_object_or_404(GroupMembership, group=g, user_id=uid)
        m.role = request.data.get("role", m.role)
        m.save(update_fields=["role"])
        return Response({"success": True, "data": {}, "message": "Updated.", "meta": {}})

    def delete(self, request, slug, uid):
        g = get_object_or_404(Group, slug=slug)
        if not GroupMembership.objects.filter(group=g, user=request.user, role__in=["admin", "moderator"], status="active").exists():
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Mod only.", "details": {}}}, status=403)
        GroupMembership.objects.filter(group=g, user_id=uid).delete()
        return Response({"success": True, "data": {}, "message": "Removed.", "meta": {}}, status=204)


class GroupPostsView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PostListSerializer

    def get(self, request, slug):
        g = get_object_or_404(Group, slug=slug)
        qs = Post.objects.filter(group=g).exclude(is_on_hold=True).order_by("-created_at")[:50]
        return Response(
            {
                "success": True,
                "data": PostListSerializer(qs, many=True, context={"request": request}).data,
                "message": "",
                "meta": {},
            }
        )

    def post(self, request, slug):
        g = get_object_or_404(Group, slug=slug)
        if not GroupMembership.objects.filter(group=g, user=request.user, status="active").exists():
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Not a member.", "details": {}}}, status=403)
        p = Post.objects.create(
            author=request.user,
            content=sanitize_html(request.data.get("content", "")),
            post_type=request.data.get("post_type", "text"),
            privacy="public",
            group=g,
        )
        g.posts_count = Post.objects.filter(group=g).count()
        g.save(update_fields=["posts_count"])
        return Response(
            {"success": True, "data": {"id": str(p.id)}, "message": "Posted.", "meta": {}},
            status=201,
        )


class GroupPendingView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupMembershipSerializer

    def get(self, request, slug):
        g = get_object_or_404(Group, slug=slug)
        if not GroupMembership.objects.filter(group=g, user=request.user, role__in=["admin", "moderator"], status="active").exists():
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Mod only.", "details": {}}}, status=403)
        qs = GroupMembership.objects.filter(group=g, status="pending")
        from apps.accounts.serializers import UserPublicSerializer

        users = [m.user for m in qs]
        return Response(
            {
                "success": True,
                "data": UserPublicSerializer(users, many=True, context={"request": request}).data,
                "message": "",
                "meta": {},
            }
        )


class GroupApproveView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def post(self, request, slug, uid):
        g = get_object_or_404(Group, slug=slug)
        if not GroupMembership.objects.filter(group=g, user=request.user, role__in=["admin", "moderator"], status="active").exists():
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Mod only.", "details": {}}}, status=403)
        GroupMembership.objects.filter(group=g, user_id=uid, status="pending").update(status="active")
        return Response({"success": True, "data": {}, "message": "Approved.", "meta": {}})


class GroupBanView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def post(self, request, slug, uid):
        g = get_object_or_404(Group, slug=slug)
        if not GroupMembership.objects.filter(group=g, user=request.user, role__in=["admin", "moderator"], status="active").exists():
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Mod only.", "details": {}}}, status=403)
        GroupMembership.objects.filter(group=g, user_id=uid).update(status="banned")
        return Response({"success": True, "data": {}, "message": "Banned.", "meta": {}})
