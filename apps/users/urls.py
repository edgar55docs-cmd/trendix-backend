from django.urls import path
from .views import (app_start,
                    google_auth,
                    setup_profile,
                    me,
                    search_users,
                    get_user_by_id,
                    check_username,
                    apple_login,
                    check_name,
                    send_verification_code,
                    verify_code,
                    logs)

urlpatterns = [
    path("start/", app_start),
    path("auth/google/", google_auth),
    path("profile/setup/", setup_profile),
    path("me/", me),
    path("search/", search_users),
    path("<int:user_id>/", get_user_by_id),
    path("check-username/", check_username),
    path("check-name/", check_name),
    path("auth/apple/", apple_login),
    path("auth/email/send-code/", send_verification_code),
    path("auth/email/verify-code/", verify_code),
    path('logs/', logs),
]