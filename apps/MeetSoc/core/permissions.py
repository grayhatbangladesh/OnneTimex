"""
Custom DRF permission classes.
"""
from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Object must have `user` or `author` or `owner` matching request.user.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        for attr in ("user", "author", "owner", "seller"):
            if hasattr(obj, attr):
                return getattr(obj, attr) == user
        return False


class IsGroupMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        from apps.MeetSoc.models import GroupMembership

        group = getattr(obj, "group", obj)
        return GroupMembership.objects.filter(
            group=group, user=request.user, status="active"
        ).exists()


class IsGroupModerator(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        from apps.MeetSoc.models import GroupMembership

        group = getattr(obj, "group", obj)
        m = GroupMembership.objects.filter(
            group=group, user=request.user, status="active"
        ).first()
        if not m:
            return False
        return m.role in ("admin", "moderator")


class IsPageAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        from apps.MeetSoc.models import PageAdmin

        page = getattr(obj, "page", obj)
        role = (
            PageAdmin.objects.filter(page=page, user=request.user)
            .values_list("role", flat=True)
            .first()
        )
        if not role:
            return False
        return role in ("owner", "admin", "editor", "analyst")


class PageAccountCannot(permissions.BasePermission):
    """
    When acting as a page, block certain actions.
    Apply to views where pages should NOT be allowed.
    """

    def has_permission(self, request, view):
        if not getattr(request, "acting_as_page", None):
            return True
        return False
