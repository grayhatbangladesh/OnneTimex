from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetSoc.models import Comment
from apps.MeetSoc.models import Post
from apps.MeetSoc.models import Reaction
from apps.MeetSoc.serializers import ReactionSerializer


class PostReactView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReactionSerializer

    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        rtype = request.data.get("type", "like")
        ct = ContentType.objects.get_for_model(Post)
        Reaction.objects.update_or_create(
            user=request.user,
            content_type=ct,
            object_id=post.id,
            defaults={"reaction_type": rtype},
        )
        self._rebuild_counts(post)
        return Response({"success": True, "data": {"reaction_type": rtype}, "message": "", "meta": {}})

    def delete(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        ct = ContentType.objects.get_for_model(Post)
        Reaction.objects.filter(user=request.user, content_type=ct, object_id=post.id).delete()
        self._rebuild_counts(post)
        return Response({"success": True, "data": {}, "message": "Removed.", "meta": {}}, status=204)

    def _rebuild_counts(self, post):
        ct = ContentType.objects.get_for_model(Post)
        qs = Reaction.objects.filter(content_type=ct, object_id=post.id)
        counts = {}
        for r in qs:
            counts[r.reaction_type] = counts.get(r.reaction_type, 0) + 1
        post.reactions_count = counts
        post.save(update_fields=["reactions_count"])


class PostReactionsListView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReactionSerializer

    def get(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        ct = ContentType.objects.get_for_model(Post)
        qs = Reaction.objects.filter(content_type=ct, object_id=post.id)
        counts = {}
        for r in qs:
            counts[r.reaction_type] = counts.get(r.reaction_type, 0) + 1
        return Response(
            {
                "success": True,
                "data": {"counts": counts, "total": qs.count()},
                "message": "",
                "meta": {},
            }
        )


class CommentReactView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReactionSerializer

    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, pk=comment_id)
        rtype = request.data.get("type", "like")
        ct = ContentType.objects.get_for_model(Comment)
        Reaction.objects.update_or_create(
            user=request.user,
            content_type=ct,
            object_id=comment.id,
            defaults={"reaction_type": rtype},
        )
        self._rebuild(comment)
        return Response({"success": True, "data": {"reaction_type": rtype}, "message": "", "meta": {}})

    def delete(self, request, comment_id):
        comment = get_object_or_404(Comment, pk=comment_id)
        ct = ContentType.objects.get_for_model(Comment)
        Reaction.objects.filter(user=request.user, content_type=ct, object_id=comment.id).delete()
        self._rebuild(comment)
        return Response({"success": True, "data": {}, "message": "Removed.", "meta": {}}, status=204)

    def _rebuild(self, comment):
        ct = ContentType.objects.get_for_model(Comment)
        qs = Reaction.objects.filter(content_type=ct, object_id=comment.id)
        counts = {}
        for r in qs:
            counts[r.reaction_type] = counts.get(r.reaction_type, 0) + 1
        comment.reactions_count = counts
        comment.save(update_fields=["reactions_count"])
