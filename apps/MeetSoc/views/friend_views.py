import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.MeetSoc.models import BlockList, Follow, Friendship, Post, PostMedia
from apps.accounts.models import UserProfile
from apps.accounts.serializers import (
    LoginTokenObtainPairSerializer,
    MeSerializer,
    MeUpdateSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    SocialTokenSerializer,
    UserPublicSerializer,
    
)
from apps.MeetSoc.services.friend_services import get_friend_suggestions
from apps.MeetSoc.core.media_processing import optimize_image
from apps.MeetSoc.core.throttling import LoginAnonThrottle, OTPThrottle
from apps.MeetSoc.core.utils import check_ip_rate_limit, check_rate_limit, sanitize_html
from apps.accounts.serializers import FriendshipSerializer, FollowSerializer

User = get_user_model()
token_generator = PasswordResetTokenGenerator()


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return MeUpdateSerializer
        return MeSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        user = self.get_object()
        
        # Ensure user has a profile
        try:
            user.profile
        except UserProfile.DoesNotExist:
            UserProfile.objects.get_or_create(user=user)
        
        # Get profile data - support both nested and flat structures
        prof_data = request.data.get("profile", {})
        if not isinstance(prof_data, dict):
            prof_data = {}
        
        # Profile field names from UserProfile model
        profile_fields = {
            "avatar", "cover_photo", "bio", "website", "work", "education",
            "relationship", "is_private", "country", "city", "hometown",
            "hobbies", "publiccontacts", "facebookUsername", "tiktokUsername",
            "youtubeUsername", "linkedinUsername", "instagramUsername",
            "twitterUsername", "snapchatUsername", "otherinfo"
        }
        
        # Extract profile fields from root request (flat structure)
        for field in profile_fields:
            if field in request.data and field not in prof_data:
                prof_data[field] = request.data[field]
        
        # Extract user fields only (exclude profile fields)
        user_data = {k: v for k, v in request.data.items() 
                     if k not in profile_fields and k != "profile"}
        
        # Update user fields if any
        if user_data:
            ser = self.get_serializer(user, data=user_data, partial=True)
            ser.is_valid(raise_exception=True)
            ser.save()
        
        # Update profile fields if any
        if prof_data:
            pser = ProfileUpdateSerializer(user.profile, data=prof_data, partial=True)
            pser.is_valid(raise_exception=True)
            pser.save()
        
        # Refresh user and profile from database to get latest data
        user.refresh_from_db()
        user.profile.refresh_from_db()
        
        return Response({"success": True, "data": MeSerializer(user).data, "message": "Updated.", "meta": {}})

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class AvatarUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeUpdateSerializer

    def patch(self, request):
        avatar = request.FILES.get("avatar")
        if not avatar:
            return Response({"success": False, "error": {"code": "REQUIRED", "message": "avatar file required.", "details": {}}}, status=400)
        request.user.profile.avatar = optimize_image(avatar)
        request.user.profile.save(update_fields=["avatar"])
        return Response({"success": True, "data": UserPublicSerializer(request.user).data, "message": "", "meta": {}})


class CoverUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeUpdateSerializer

    def patch(self, request):
        cover = request.FILES.get("cover_photo")
        if not cover:
            return Response({"success": False, "error": {"code": "REQUIRED", "message": "cover_photo required.", "details": {}}}, status=400)
        request.user.profile.cover_photo = optimize_image(cover)
        request.user.profile.save(update_fields=["cover_photo"])
        return Response({"success": True, "data": UserPublicSerializer(request.user).data, "message": "", "meta": {}})


class PublicProfileView(generics.RetrieveAPIView):
    lookup_field = "id"  
    # URL এ আপনি যেহেতু 'user_id' লিখেছেন, তাই নিচের লাইনটি যোগ করুন
    lookup_url_kwarg = "user_id"
    queryset = User.objects.select_related("profile")
    serializer_class = UserPublicSerializer
    permission_classes = [AllowAny]


class UsernameProfileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        return Response(
            {"success": True, "data": UserPublicSerializer(user, context={"request": request}).data, "message": "", "meta": {}}
        )


class UserPostsView(generics.ListAPIView):
    serializer_class = None
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        qs = Post.objects.filter(author=user, privacy="public").order_by("-created_at")[:50]
        from apps.MeetSoc.serializers import PostListSerializer

        data = PostListSerializer(qs, many=True, context={"request": request}).data
        return Response({"success": True, "data": data, "message": "", "meta": {}})


class UserPhotosView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        media = PostMedia.objects.filter(post__author=user, media_type="image")[:100]
        urls = [request.build_absolute_uri(m.file.url) if m.file else "" for m in media]
        return Response({"success": True, "data": {"photos": urls}, "message": "", "meta": {}})


class UserVideosView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        from apps.MeetSoc.models import WatchVideo
        from apps.MeetSoc.models import Post

        data = []

        for v in WatchVideo.objects.filter(author=user).exclude(is_on_hold=True).order_by("-created_at")[:50]:
            data.append({
                "id": str(v.id),
                "title": v.title,
                "description": v.description,
                "video_file": request.build_absolute_uri(v.video_file.url) if v.video_file else "",
                "thumbnail": request.build_absolute_uri(v.thumbnail.url) if v.thumbnail else "",
                "duration": v.duration,
                "views_count": v.views_count,
                "created_at": v.created_at.isoformat() if v.created_at else "",
                "source": "watch",
            })

        for p in Post.objects.filter(author=user, post_type="video").exclude(is_on_hold=True).order_by("-created_at")[:50]:
            media = p.media_items.filter(media_type="video").first()
            if media and media.file:
                data.append({
                    "id": str(p.id),
                    "title": p.content[:100] if p.content else "",
                    "description": p.content or "",
                    "video_file": request.build_absolute_uri(media.file.url),
                    "thumbnail": request.build_absolute_uri(media.thumbnail.url) if media.thumbnail else "",
                    "duration": None,
                    "views_count": 0,
                    "created_at": p.created_at.isoformat() if p.created_at else "",
                    "source": "post",
                })

        data.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return Response({"success": True, "data": {"videos": data}, "message": "", "meta": {}})


class UserFriendsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        ids = Friendship.objects.filter(
            Q(sender=user, status="accepted") | Q(receiver=user, status="accepted")
        )
        friends = []
        for f in ids:
            other = f.receiver if f.sender_id == user.id else f.sender
            friends.append(UserPublicSerializer(other).data)
        return Response({"success": True, "data": friends, "message": "", "meta": {}})


class MyFriendsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        friendships = Friendship.objects.filter(
            Q(sender=request.user, status="accepted") | Q(receiver=request.user, status="accepted")
        )
        friends = []
        for f in friendships:
            other = f.receiver if f.sender_id == request.user.id else f.sender
            friends.append(UserPublicSerializer(other, context={"request": request}).data)
        return Response({"success": True, "data": friends, "message": "", "meta": {}})


class FollowersListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        qs = User.objects.filter(following_rel__following=user)
        return Response(
            {
                "success": True,
                "data": UserPublicSerializer(qs[:100], many=True).data,
                "message": "",
                "meta": {},
            }
        )


class FollowingListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        qs = User.objects.filter(follower_rel__follower=user)
        return Response(
            {
                "success": True,
                "data": UserPublicSerializer(qs[:100], many=True).data,
                "message": "",
                "meta": {},
            }
        )


class FriendRequestView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FriendshipSerializer

    def post(self, request, user_id):
        other = get_object_or_404(User, pk=user_id)
        if other.id == request.user.id:
            return Response({"success": False, "error": {"code": "INVALID", "message": "Cannot friend self.", "details": {}}}, status=400)
        fr, created = Friendship.objects.update_or_create(
            sender=request.user,
            receiver=other,
            defaults={"status": "pending"},
        )
        if created:
            try:
                from apps.MeetSoc.tasks.notification_tasks import notify
                notify(
                    recipient_id=other.id,
                    actor_id=request.user.id,
                    notification_type="friend_request",
                    verb=f"{request.user.full_name or request.user.username} sent you a friend request",
                    data={"user_id": str(request.user.id)},
                    target_type="user",
                    target_id=request.user.id,
                )
            except Exception:
                pass
        # Return updated friendship status for immediate UI update
        friendship_status = "request_sent" if request.user.id < other.id else "request_received"
        is_following = False
        try:
            from apps.MeetSoc.models import Follow
            is_following = Follow.objects.filter(follower=request.user, following=other).exists()
        except Exception:
            pass
        return Response({
            "success": True,
            "data": {
                "friendshipStatus": friendship_status,
                "isFollowing": is_following,
                "requestSent": True,
                "requestReceived": False,
            },
            "message": "Request sent.",
            "meta": {},
        })


class FriendAcceptView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FriendshipSerializer

    def post(self, request, user_id):
        other = get_object_or_404(User, pk=user_id)
        fr = Friendship.objects.filter(sender=other, receiver=request.user, status="pending").first()
        if not fr:
            return Response({"success": False, "error": {"code": "NOT_FOUND", "message": "No pending request.", "details": {}}}, status=404)
        fr.status = "accepted"
        fr.save()
        for u, p in ((request.user, request.user.profile), (other, other.profile)):
            p.friends_count = Friendship.objects.filter(
                Q(sender=u, status="accepted") | Q(receiver=u, status="accepted")
            ).count()
            p.save(update_fields=["friends_count"])

        try:
            from apps.MeetSoc.tasks.notification_tasks import notify
            notify(
                recipient_id=other.id,
                actor_id=request.user.id,
                notification_type="friend_accept",
                verb=f"{request.user.full_name or request.user.username} accepted your friend request",
                data={"user_id": str(request.user.id)},
                target_type="user",
                target_id=request.user.id,
            )
        except Exception:
            pass

        # Return updated friendship status for immediate UI update
        return Response({
            "success": True,
            "data": {
                "friendshipStatus": "friends",
                "isFollowing": True,
                "accepted": True,
            },
            "message": "Accepted.",
            "meta": {},
        })


class FriendDeclineView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FriendshipSerializer

    def post(self, request, user_id):
        other = get_object_or_404(User, pk=user_id)
        Friendship.objects.filter(sender=other, receiver=request.user, status="pending").update(status="declined")
        return Response({
            "success": True,
            "data": {"friendshipStatus": "none", "declined": True},
            "message": "Declined.",
            "meta": {},
        })


class FriendUnfriendView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def delete(self, request, user_id):
        other = get_object_or_404(User, pk=user_id)
        Friendship.objects.filter(
            Q(sender=request.user, receiver=other) | Q(sender=other, receiver=request.user)
        ).delete()
        return Response({
            "success": True,
            "data": {"friendshipStatus": "none", "unfriended": True},
            "message": "Unfriended.",
            "meta": {},
        })


class FriendRequestsListView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FriendshipSerializer

    def get(self, request):
        qs = Friendship.objects.filter(receiver=request.user, status="pending")
        from apps.accounts.serializers import FriendshipSerializer

        limit = request.query_params.get("limit")
        if limit:
            try:
                qs = qs[: int(limit)]
            except (ValueError, TypeError):
                pass

        page = request.query_params.get("page")
        if page:
            from apps.MeetSoc.core.pagination import StandardPagination

            paginator = StandardPagination()
            paginator.page_size = int(request.query_params.get("page_size", 30))
            page_obj = paginator.paginate_queryset(qs, request)
            return paginator.get_paginated_response(
                FriendshipSerializer(page_obj, many=True).data
            )

        return Response(
            {
                "success": True,
                "data": FriendshipSerializer(qs, many=True).data,
                "message": "",
                "meta": {},
            }
        )


class FriendRequestsOutgoingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Friendship.objects.filter(sender=request.user, status="pending")
        from apps.accounts.serializers import FriendshipSerializer

        page = request.query_params.get("page")
        if page:
            from apps.MeetSoc.core.pagination import StandardPagination

            paginator = StandardPagination()
            paginator.page_size = int(request.query_params.get("page_size", 30))
            page_obj = paginator.paginate_queryset(qs, request)
            return paginator.get_paginated_response(
                FriendshipSerializer(page_obj, many=True).data
            )

        return Response(
            {
                "success": True,
                "data": FriendshipSerializer(qs, many=True).data,
                "message": "",
                "meta": {},
            }
        )


class FriendSuggestionsView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserPublicSerializer

    def get(self, request):
        suggestions = get_friend_suggestions(request.user, limit=30)
        users = [u for _, u in suggestions]
        return Response(
            {
                "success": True,
                "data": UserPublicSerializer(users, many=True).data,
                "message": "",
                "meta": {},
            }
        )


class FollowUserView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FollowSerializer

    def post(self, request, user_id):
        other = get_object_or_404(User, pk=user_id)
        if other.id == request.user.id:
            return Response({"success": False, "error": {"code": "INVALID", "message": "Cannot follow self.", "details": {}}}, status=400)
        _, created = Follow.objects.get_or_create(follower=request.user, following=other)
        other.profile.followers_count = Follow.objects.filter(following=other).count()
        request.user.profile.following_count = Follow.objects.filter(follower=request.user).count()
        other.profile.save(update_fields=["followers_count"])
        request.user.profile.save(update_fields=["following_count"])

        if created:
            try:
                from apps.MeetSoc.tasks.notification_tasks import notify
                notify(
                    recipient_id=other.id,
                    actor_id=request.user.id,
                    notification_type="follow",
                    verb=f"{request.user.full_name or request.user.username} started following you",
                    data={"user_id": str(request.user.id)},
                    target_type="user",
                    target_id=request.user.id,
                )
            except Exception:
                pass

        return Response({
            "success": True,
            "data": {"isFollowing": True, "followingCount": request.user.profile.following_count},
            "message": "Followed.",
            "meta": {},
        })


class UnfollowUserView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def delete(self, request, user_id):
        other = get_object_or_404(User, pk=user_id)
        Follow.objects.filter(follower=request.user, following=other).delete()
        return Response({
            "success": True,
            "data": {"isFollowing": False, "followingCount": request.user.profile.following_count},
            "message": "Unfollowed.",
            "meta": {},
        })


class BlockUserView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def post(self, request, user_id):
        other = get_object_or_404(User, pk=user_id)
        BlockList.objects.get_or_create(blocker=request.user, blocked=other)
        return Response({
            "success": True,
            "data": {"blocked": True, "blockedUserId": str(user_id)},
            "message": "Blocked.",
            "meta": {},
        })


class UnblockUserView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    def delete(self, request, user_id):
        other = get_object_or_404(User, pk=user_id)
        BlockList.objects.filter(blocker=request.user, blocked=other).delete()
        return Response({
            "success": True,
            "data": {"blocked": False, "unblockedUserId": str(user_id)},
            "message": "Unblocked.",
            "meta": {},
        })


class BlockedListView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserPublicSerializer

    def get(self, request):
        qs = User.objects.filter(blocked_by__blocker=request.user)
        return Response(
            {
                "success": True,
                "data": UserPublicSerializer(qs, many=True).data,
                "message": "",
                "meta": {},
            }
        )


class PeopleYouMayKnowView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserPublicSerializer

    def get(self, request):
        suggestions = get_friend_suggestions(request.user, limit=20)
        users = [u for _, u in suggestions]
        return Response(
            {
                "success": True,
                "data": UserPublicSerializer(users, many=True).data,
                "message": "",
                "meta": {},
            }
        )
