from django.urls import path

from apps.MeetSoc import views as v

urlpatterns = [
    path("notifications/", v.NotificationListView.as_view(), name="notifications-list"),
    path("notifications/mark-read/", v.NotificationMarkAllReadView.as_view(), name="notifications-mark-read"),
    path("notifications/<uuid:notification_id>/read/", v.NotificationReadView.as_view(), name="notifications-read"),
    path("notifications/<uuid:notification_id>/", v.NotificationDeleteView.as_view(), name="notifications-delete"),
    path("notifications/unread-count/", v.NotificationUnreadCountView.as_view(), name="notifications-unread"),
    path("notifications/settings/", v.NotificationSettingsView.as_view(), name="notifications-settings"),
    path("notifications/fcm-token/", v.FCMTokenView.as_view(), name="notifications-fcm"),
]
