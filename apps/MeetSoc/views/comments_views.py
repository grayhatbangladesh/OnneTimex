from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetSoc.models import Comment, CommentReaction
from apps.MeetSoc.serializers import CommentSerializer, CommentDetailSerializer
from apps.MeetSoc.models import Post
from apps.MeetSoc.core.pagination import StandardPagination
from apps.MeetSoc.core.utils import sanitize_html


class CommentListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    serializer_class = CommentSerializer

    def get(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        qs = Comment.objects.filter(post=post, parent__isnull=True).select_related("author", "author__profile").order_by("created_at")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        data = [
            {
                "id": str(c.id),
                "author_id": str(c.author_id),
                "author": {
                    "id": str(c.author_id),
                    "username": c.author.username,
                    "fullname": c.author.full_name or c.author.username,
                    "is_verified": c.author.is_verified,
                    "profile": {
                        "avatar": c.author.profile.avatar.url if c.author.profile and c.author.profile.avatar else None,
                        "cover_photo": c.author.profile.cover_photo.url if c.author.profile and c.author.profile.cover_photo else None,
                    } if hasattr(c.author, "profile") else None,
                },
                "content": c.content,
                "media": c.media.url if c.media else None,
                "reactions_count": c.reactions_count,
                "replies_count": c.replies_count,
                "is_edited": c.is_edited,
                "created_at": c.created_at.isoformat(),
            }
            for c in page
        ]
        return paginator.get_paginated_response(data)

    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        content = sanitize_html(request.data.get("content", ""))
        media_file = request.FILES.get("media")
        c = Comment.objects.create(post=post, author=request.user, content=content, media=media_file)
        post.comments_count = Comment.objects.filter(post=post, parent__isnull=True).count()
        post.save(update_fields=["comments_count"])

        if post.author_id != request.user.id:
            from apps.MeetSoc.tasks.notification_tasks import notify
            notify(
                recipient_id=post.author_id,
                actor_id=request.user.id,
                notification_type="post_comment",
                verb=f"{request.user.full_name or request.user.username} commented on your post",
                data={"post_id": str(post.id), "comment_id": str(c.id)},
                target_type="post",
                target_id=post.id,
            )

        return Response(
            {
                "success": True,
                "data": {
                    "id": str(c.id),
                    "author_id": str(c.author_id),
                    "author": {
                        "id": str(c.author_id),
                        "username": c.author.username,
                        "fullname": c.author.full_name or c.author.username,
                        "is_verified": c.author.is_verified,
                        "profile": {
                            "avatar": c.author.profile.avatar.url if c.author.profile and c.author.profile.avatar else None,
                            "cover_photo": c.author.profile.cover_photo.url if c.author.profile and c.author.profile.cover_photo else None,
                        } if hasattr(c.author, "profile") else None,
                    },
                    "content": c.content,
                    "reactions_count": c.reactions_count,
                    "replies_count": c.replies_count,
                    "is_edited": c.is_edited,
                    "created_at": c.created_at.isoformat(),
                },
                "message": "Comment added.",
                "meta": {},
            },
            status=201,
        )


class CommentDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CommentDetailSerializer

    def put(self, request, comment_id):
        c = get_object_or_404(Comment, pk=comment_id, author=request.user)
        c.content = sanitize_html(request.data.get("content", c.content))
        c.is_edited = True
        c.save()
        return Response({"success": True, "data": {"id": str(c.id)}, "message": "Updated.", "meta": {}})

    def delete(self, request, comment_id):
        c = get_object_or_404(Comment, pk=comment_id, author=request.user)
        post = c.post
        c.delete()
        post.comments_count = Comment.objects.filter(post=post, parent__isnull=True).count()
        post.save(update_fields=["comments_count"])
        return Response({"success": True, "data": {}, "message": "Deleted.", "meta": {}}, status=204)


class CommentReplyListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CommentSerializer

    def post(self, request, comment_id):
        parent = get_object_or_404(Comment, pk=comment_id)
        content = sanitize_html(request.data.get("content", ""))
        media_file = request.FILES.get("media")
        c = Comment.objects.create(
            post=parent.post,
            author=request.user,
            parent=parent,
            content=content,
            media=media_file,
        )
        parent.replies_count = Comment.objects.filter(parent=parent).count()
        parent.save(update_fields=["replies_count"])

        if parent.author_id != request.user.id:
            from apps.MeetSoc.tasks.notification_tasks import notify
            notify(
                recipient_id=parent.author_id,
                actor_id=request.user.id,
                notification_type="comment_reply",
                verb=f"{request.user.full_name or request.user.username} replied to your comment",
                data={"post_id": str(parent.post_id), "comment_id": str(c.id), "parent_id": str(parent.id)},
                target_type="comment",
                target_id=parent.id,
            )

        return Response(
            {"success": True, "data": {"id": str(c.id), "parent_id": str(parent.id)}, "message": "Reply added.", "meta": {}},
            status=201,
        )

    def get(self, request, comment_id):
        parent = get_object_or_404(Comment, pk=comment_id)
        qs = Comment.objects.filter(parent=parent).select_related("author", "author__profile").order_by("created_at")
        data = [
            {
                "id": str(c.id),
                "parent_id": str(c.parent_id) if c.parent_id else None,
                "author_id": str(c.author_id),
                "author": {
                    "id": str(c.author_id),
                    "username": c.author.username,
                    "fullname": c.author.full_name or c.author.username,
                    "is_verified": c.author.is_verified,
                    "profile": {
                        "avatar": c.author.profile.avatar.url if c.author.profile and c.author.profile.avatar else None,
                        "cover_photo": c.author.profile.cover_photo.url if c.author.profile and c.author.profile.cover_photo else None,
                    } if hasattr(c.author, "profile") else None,
                },
                "content": c.content,
                "media": c.media.url if c.media else None,
                "reactions_count": c.reactions_count,
                "created_at": c.created_at.isoformat(),
            }
            for c in qs
        ]
        return Response({"success": True, "data": data, "message": "", "meta": {}})


class CommentReactView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, pk=comment_id)
        reaction_type = request.data.get("reaction_type", "like")

        existing = CommentReaction.objects.filter(comment=comment, user=request.user).first()
        if existing:
            if existing.reaction_type == reaction_type:
                existing.delete()
                comment.reactions_count[reaction_type] = max(0, comment.reactions_count.get(reaction_type, 1) - 1)
                if comment.reactions_count[reaction_type] == 0:
                    comment.reactions_count.pop(reaction_type, None)
                comment.save(update_fields=["reactions_count"])
                return Response({"success": True, "data": {"reacted": False, "reaction_type": None, "reactions_count": comment.reactions_count}, "message": "Removed.", "meta": {}})
            else:
                old_type = existing.reaction_type
                existing.reaction_type = reaction_type
                existing.save()
                comment.reactions_count[old_type] = max(0, comment.reactions_count.get(old_type, 1) - 1)
                if comment.reactions_count[old_type] == 0:
                    comment.reactions_count.pop(old_type, None)
                comment.reactions_count[reaction_type] = comment.reactions_count.get(reaction_type, 0) + 1
                comment.save(update_fields=["reactions_count"])
                self._notify_reactor(request.user, comment, reaction_type)
                return Response({"success": True, "data": {"reacted": True, "reaction_type": reaction_type, "reactions_count": comment.reactions_count}, "message": "Updated.", "meta": {}})
        else:
            CommentReaction.objects.create(comment=comment, user=request.user, reaction_type=reaction_type)
            comment.reactions_count[reaction_type] = comment.reactions_count.get(reaction_type, 0) + 1
            comment.save(update_fields=["reactions_count"])
            self._notify_reactor(request.user, comment, reaction_type)
            return Response({"success": True, "data": {"reacted": True, "reaction_type": reaction_type, "reactions_count": comment.reactions_count}, "message": "Liked.", "meta": {}})

    @staticmethod
    def _notify_reactor(actor, comment, reaction_type):
        """Tell the comment author somebody reacted (no notification on remove)."""
        if comment.author_id == actor.id:
            return
        try:
            from apps.MeetSoc.tasks.notification_tasks import notify
            notify(
                recipient_id=comment.author_id,
                actor_id=actor.id,
                notification_type="post_like",
                verb=f"{actor.full_name or actor.username} reacted to your comment",
                data={
                    "comment_id": str(comment.id),
                    "post_id": str(comment.post_id),
                    "reaction_type": reaction_type,
                },
                target_type="comment",
                target_id=comment.id,
            )
        except Exception:
            pass
