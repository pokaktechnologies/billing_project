from django.urls import path
from .views import SignupView, OTPVerificationView, GettingStartedView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    
    path('signup/', SignupView.as_view(), name='signup'),
    path('verify-otp/', OTPVerificationView.as_view(), name='verify_otp'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('getting-started/', GettingStartedView.as_view(), name='getting_started'),

]
