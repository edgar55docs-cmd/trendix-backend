from django.urls import path
from apps.users.refresh import CustomTokenRefreshView
from .views import (register,
                    app_start,
                    logs,
                    google_auth,
                    apple_auth,
                    send_code,
                    verify_code,
                    setup_profile,
                    get_me,
                    login,
                    reset_password,
                    upload_cover,
                    search_users,
                    get_user_profile)

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
    path('auth/token/refresh/', CustomTokenRefreshView.as_view()),
    path("auth/login/", login),
    path('auth/reset-password/', reset_password),
    path("upload-cover/", upload_cover),
    path("search/", search_users),
    path('<int:user_id>/', get_user_profile),

]