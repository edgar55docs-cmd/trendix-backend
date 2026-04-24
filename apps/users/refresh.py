from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.response import Response
from rest_framework import status
from .models import UserSession

class CustomTokenRefreshView(TokenRefreshView):

    def post(self, request, *args, **kwargs):

        refresh_token = request.data.get("refresh")
        device_id = request.headers.get("Device-Id")

        print("🔄 REFRESH DEVICE:", device_id)

        session = UserSession.objects.filter(
            refresh_token=refresh_token,
            device_id=device_id
        ).first()

        if not session:
            return Response(
                {"error": "Invalid device session"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return super().post(request, *args, **kwargs)