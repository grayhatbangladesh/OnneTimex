"""Sidebar views: the right rail (sponsored / contacts / groups)."""
from django.core.cache import cache
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


def _image_url(field):
    """ImageField -> url, never raising (unsaved/missing file -> "")."""
    try:
        return field.url if field else ""
    except Exception:
        return ""


def _avatar_url(user):
    try:
        from apps.accounts.serializers import _avatar_url as resolve

        return resolve(user)
    except Exception:
        return ""


class SidebarView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {"menu_items": [], "ads": [], "contacts": [], "groups": []}

        # --- Your groups (membership, most recently joined first) -----------
        try:
            from apps.MeetSoc.models import GroupMembership

            rows = (
                GroupMembership.objects.filter(user=request.user, status="active")
                .select_related("group")
                .order_by("-joined_at")[:12]
            )
            data["groups"] = [
                {
                    "id": str(row.group_id),
                    "name": row.group.name,
                    "slug": row.group.slug,
                    "cover": _image_url(row.group.cover_photo),
                    "avatar": _image_url(row.group.avatar),
                    "members_count": row.group.members_count,
                    "category": row.group.category,
                }
                for row in rows
                if row.group_id
            ]
        except Exception:
            pass

        # --- Friends (accepted), with live online flag ---------------------
        try:
            from apps.MeetSoc.models import Friendship

            pairs = (
                Friendship.objects.filter(
                    Q(sender=request.user) | Q(receiver=request.user),
                    status="accepted",
                )
                .select_related("sender", "receiver")[:20]
            )
            contacts = []
            for pair in pairs:
                other = pair.receiver if pair.sender_id == request.user.id else pair.sender
                if other is None or other.id == request.user.id:
                    continue
                contacts.append(
                    {
                        "id": str(other.id),
                        "name": other.full_name or other.username,
                        "avatar": _avatar_url(other),
                        "online": bool(cache.get(f"online:{other.id}")),
                    }
                )
            data["contacts"] = contacts
        except Exception:
            pass

        # --- Sponsored: no ads app in this project yet ----------------------
        data["ads"] = []

        return Response({"success": True, "data": data, "message": "", "meta": {}})
