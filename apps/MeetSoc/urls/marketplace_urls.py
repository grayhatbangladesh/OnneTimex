from django.urls import path

from apps.MeetSoc import views as v

urlpatterns = [
    path("marketplace/products/", v.ProductListCreateView.as_view(), name="marketplace-products"),
    path("marketplace/products/<uuid:product_id>/", v.ProductDetailView.as_view(), name="marketplace-product-detail"),
]
