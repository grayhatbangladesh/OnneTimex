from django.urls import path

from apps.MeetSoc import views as v

urlpatterns = [
    path("admin/stats/", v.AdminStatsView.as_view(), name="admin-stats"),
    # Users — plain list, then <uuid> detail, then the optional <query>
    # suffix route (registered last so it never shadows the detail view).
    path("admin/users/", v.AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/<uuid:user_id>/", v.AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/users/<str:query>/", v.AdminUserListView.as_view(), name="admin-user-list-query"),
    path("admin/verification/", v.AdminVerificationListView.as_view(), name="admin-verification-list"),
    path(
        "admin/verification/<uuid:verification_id>/",
        v.AdminVerificationActionView.as_view(),
        name="admin-verification-action",
    ),
    path("admin/posts/", v.AdminPostListView.as_view(), name="admin-post-list"),
    path("admin/posts/<uuid:post_id>/", v.AdminPostDeleteView.as_view(), name="admin-post-delete"),
    path("admin/posts/<str:query>/", v.AdminPostListView.as_view(), name="admin-post-list-query"),
    path("admin/groups/", v.AdminGroupListView.as_view(), name="admin-group-list"),
    path("admin/groups/<uuid:group_id>/", v.AdminGroupDeleteView.as_view(), name="admin-group-delete"),
    path("admin/pages/", v.AdminPageListView.as_view(), name="admin-page-list"),
    path("admin/pages/<uuid:page_id>/", v.AdminPageDetailView.as_view(), name="admin-page-detail"),
    path("admin/products/", v.AdminProductListView.as_view(), name="admin-product-list"),
    path(
        "admin/products/<uuid:product_id>/",
        v.AdminProductDetailView.as_view(),
        name="admin-product-detail",
    ),
    path("admin/products/<str:query>/", v.AdminProductListView.as_view(), name="admin-product-list-query"),
    path("admin/videos/", v.AdminVideoListView.as_view(), name="admin-video-list"),
    path("admin/videos/<uuid:video_id>/", v.AdminVideoDeleteView.as_view(), name="admin-video-delete"),
    path("admin/ads/", v.AdminAdListView.as_view(), name="admin-ad-list"),
    path("admin/ads/<str:ad_id>/", v.AdminAdActionView.as_view(), name="admin-ad-action"),
    path("admin/payments/", v.AdminPaymentsListView.as_view(), name="admin-payment-list"),
    path(
        "admin/payments/<uuid:payment_id>/",
        v.AdminPaymentsActionView.as_view(),
        name="admin-payment-action",
    ),
    path(
        "admin/suspensions/",
        v.AdminSuspensionListCreateView.as_view(),
        name="admin-suspension-list-create",
    ),
    path(
        "admin/suspensions/<uuid:suspension_id>/",
        v.AdminSuspensionDeleteView.as_view(),
        name="admin-suspension-delete",
    ),
]
