from django.contrib import admin
from .models import UserProfile, User
# Register your models here.

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_private", "posts_count", "friends_count", "following_count", "created_at")
    list_filter = ("is_private", "created_at")
    search_fields = ("user__username", "user__email", "public_contacts")
    readonly_fields = ("posts_count", "friends_count", "followers_count", "following_count", "created_at", "updated_at")


admin.site.register(User)    