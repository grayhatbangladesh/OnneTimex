from django.urls import path
from apps.MeetSoc import views as v

urlpatterns = [
    path("categories/", v.CategoryListView.as_view(), name="categories-list"),
    path("tags/", v.TagListView.as_view(), name="tags-list"),
]
