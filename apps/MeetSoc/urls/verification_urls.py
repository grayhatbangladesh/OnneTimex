from django.urls import path

from apps.MeetSoc import views as v

urlpatterns = [
    path("verification/plans/", v.SubscriptionPlanListView.as_view(), name="verification-plans"),
    path("verification/blue/apply/", v.BlueVerificationApplyView.as_view(), name="verification-blue-apply"),
    path("verification/blue/my-status/", v.BlueVerificationMyStatusView.as_view(), name="verification-blue-status"),
    path("verification/purchase/", v.PurchaseSubscriptionView.as_view(), name="verification-purchase"),
    path("verification/payment-methods/", v.PaymentMethodListView.as_view(), name="verification-payment-methods"),
]
