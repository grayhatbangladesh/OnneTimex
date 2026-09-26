from django.urls import path
from apps.MeetSoc import views as v

urlpatterns = [
    path("ads/plans/", v.AdsPlansView.as_view(), name="ads-plans"),
    path("ads/", v.AdsListView.as_view(), name="ads-list"),
    path("ads/<str:ad_id>/", v.AdsDetailView.as_view(), name="ads-detail"),
    path("ads/<str:ad_id>/pay/", v.AdsPayView.as_view(), name="ads-pay"),
    path("ads/<str:ad_id>/action/", v.AdsActionView.as_view(), name="ads-action"),
    path("ads/<str:ad_id>/impression/", v.AdsImpressionView.as_view(), name="ads-impression"),
    path("ads/<str:ad_id>/analytics/", v.AdsAnalyticsView.as_view(), name="ads-analytics"),
    path("ads/feed/", v.AdsFeedView.as_view(), name="ads-feed"),
]
