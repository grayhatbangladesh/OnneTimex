from django.contrib import admin
from .models.comments import Comment, CommentReaction
from .models.posts import Post, Story, PostMedia
from .models.friends import Friendship, Follow, BlockList
from .models.groups import Group, GroupMembership, GroupInvite
from .models.pages import Page, PageAdmin, PageFollower
from .models.marketplace import Product, ProductMedia
from .models.notifications import Notification, NotificationSettings
from .models.payments import Payment, PaymentMethod, UserWallet, WalletTransaction
from .models.reports import Report
from .models.verification import SubscriptionPlan, BlueVerificationRequest, UserSubscription
from .models.watch import WatchVideo, WatchVideoComment
from .models.reactions import Reaction
from .models.search import TrendingTopic
from .models.memories import Memory
from .models.feed import SavedPost, FeedHide, FeedSnooze, RecentSearch


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(Page)
class PageModelAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(PageAdmin)
class PageAdminDetailAdmin(admin.ModelAdmin):
    list_display = ("id", "page", "user")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "title")


@admin.register(ProductMedia)
class ProductMediaAdmin(admin.ModelAdmin):
    list_display = ("id", "product")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "author")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "content")


@admin.register(PostMedia)
class PostMediaAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "media_type")


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "media_type")


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ("id", "sender", "receiver")


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("id", "follower", "following")


@admin.register(BlockList)
class BlockListAdmin(admin.ModelAdmin):
    list_display = ("id", "blocker", "blocked")


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "group", "user", "role")


@admin.register(GroupInvite)
class GroupInviteAdmin(admin.ModelAdmin):
    list_display = ("id", "group", "invited_by")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "notification_type", "is_read")


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ("id",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "currency", "status")


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "number")


@admin.register(UserWallet)
class UserWalletAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "balance_bdt", "balance_usd")


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "wallet", "type", "amount", "currency", "status")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "reporter", "content_type", "reason", "status")


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(BlueVerificationRequest)
class BlueVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "plan", "status")


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "plan", "is_active")


@admin.register(WatchVideo)
class WatchVideoAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "category")


@admin.register(WatchVideoComment)
class WatchVideoCommentAdmin(admin.ModelAdmin):
    list_display = ("id", "video", "author")


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "reaction_type")


@admin.register(TrendingTopic)
class TrendingTopicAdmin(admin.ModelAdmin):
    list_display = ("id", "tag", "score")


@admin.register(Memory)
class MemoryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "year")


@admin.register(SavedPost)
class SavedPostAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "post")


@admin.register(FeedHide)
class FeedHideAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "post")


@admin.register(FeedSnooze)
class FeedSnoozeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "snoozed_user")


@admin.register(RecentSearch)
class RecentSearchAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "query")


@admin.register(CommentReaction)
class CommentReactionAdmin(admin.ModelAdmin):
    list_display = ("id", "comment", "user", "reaction_type")
