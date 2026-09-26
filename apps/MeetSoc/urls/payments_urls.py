from django.urls import path

from apps.MeetSoc import views as v

urlpatterns = [
    path("payments/methods/", v.PaymentMethodListView.as_view(), name="payment-methods"),
    path("payments/", v.PaymentListCreateView.as_view(), name="payment-list-create"),
    path("payments/<uuid:payment_id>/", v.PaymentDetailView.as_view(), name="payment-detail"),
    path("payments/admin/list/", v.AdminPaymentListView.as_view(), name="admin-payment-list"),
    path("payments/admin/<uuid:payment_id>/action/", v.AdminPaymentActionView.as_view(), name="admin-payment-action"),
    path("payments/wallet/", v.WalletView.as_view(), name="wallet"),
    path("payments/wallet/add/", v.WalletAddView.as_view(), name="wallet-add"),
    path("payments/wallet/history/", v.WalletHistoryView.as_view(), name="wallet-history"),
]
