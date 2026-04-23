from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (register,
                    app_start,
                    logs,
                    google_auth,
                    apple_auth,
                    send_code,
                    verify_code,
                    setup_profile,
                    get_me)

urlpatterns = [

    path("auth/register/", register),
    path("app/start/", app_start),
    path("logs/", logs),
    path("auth/google/", google_auth),
    path("auth/apple/", apple_auth),
    path("auth/send-code/", send_code, name="send_code"),
    path("auth/verify/", verify_code, name="verify_code"),
    path("profile/setup/", setup_profile),
    path('me/', get_me),
    path('auth/token/refresh/', TokenRefreshView.as_view()),

]