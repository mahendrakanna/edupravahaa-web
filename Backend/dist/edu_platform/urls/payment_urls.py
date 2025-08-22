from django.urls import path
from edu_platform.views.payment_views import CreateOrderView, VerifyPaymentView


urlpatterns = [
    # Creates a Razorpay order for a course subscription.
    path('create_order/', CreateOrderView.as_view(), name='create_order'),
    
    # Verifies payment for a subscription and updates subscription status.
    path('verify_payment/', VerifyPaymentView.as_view(), name='verify_payment'),
]