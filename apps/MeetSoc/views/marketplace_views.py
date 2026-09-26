from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.MeetSoc.models import Product, ProductMedia
from apps.MeetSoc.serializers import ProductSerializer
from apps.MeetSoc.core.media_processing import optimize_image


class ProductListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductSerializer

    def get(self, request):
        qs = Product.objects.filter(status="active").exclude(is_on_hold=True).order_by("-created_at")[:100]
        data = []
        for p in qs:
            media = list(p.media_items.all().order_by("order"))
            data.append({
                "id": str(p.id),
                "title": p.title,
                "description": p.description,
                "price": str(p.price),
                "category": p.category,
                "condition": p.condition,
                "location": p.location,
                "status": p.status,
                "views_count": p.views_count,
                "seller": {
                    "id": str(p.seller.id),
                    "username": p.seller.username,
                    "full_name": getattr(p.seller, "full_name", ""),
                    "avatar": getattr(p.seller.profile.avatar, "url", "") if hasattr(p.seller, "profile") else "",
                },
                "media": [
                    {"id": str(m.id), "file": m.file.url if m.file else "", "order": m.order}
                    for m in media
                ],
                "created_at": p.created_at.isoformat() if p.created_at else "",
            })
        return Response({"success": True, "data": data, "message": "", "meta": {}})

    def post(self, request):
        p = Product.objects.create(
            seller=request.user,
            title=request.data.get("title", "Item"),
            description=request.data.get("description", ""),
            price=Decimal(str(request.data.get("price", "0"))),
            category=request.data.get("category", ""),
            condition=request.data.get("condition", "good"),
            location=request.data.get("location") or {},
            status="pending_review",
        )
        for i, f in enumerate(request.FILES.getlist("images")):
            ProductMedia.objects.create(product=p, file=optimize_image(f), order=i)
        return Response(
            {"success": True, "data": {"id": str(p.id)}, "message": "Product submitted for review.", "meta": {}},
            status=201,
        )


class ProductDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductSerializer

    def get(self, request, product_id):
        p = get_object_or_404(Product, pk=product_id)
        if p.is_on_hold:
            return Response({"success": False, "error": {"code": "FORBIDDEN", "message": "Content unavailable.", "details": {}}}, status=403)
        p.views_count += 1
        p.save(update_fields=["views_count"])
        return Response(
            {
                "success": True,
                "data": {
                    "id": str(p.id),
                    "title": p.title,
                    "description": p.description,
                    "price": str(p.price),
                    "condition": p.condition,
                },
                "message": "",
                "meta": {},
            }
        )
