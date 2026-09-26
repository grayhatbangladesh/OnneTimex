from django.urls import path

from apps.MeetSoc import views as v

urlpatterns = [
    path("search/", v.UniversalSearchView.as_view(), name="search"),
    path("search/recent/", v.RecentSearchView.as_view(), name="search-recent"),
    path("search/trending/", v.TrendingView.as_view(), name="search-trending"),
]
