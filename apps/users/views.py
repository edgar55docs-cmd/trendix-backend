from django.contrib.auth import get_user_model
from google.oauth2 import id_token
from google.auth.transport.requests import Request
from django.utils.translation import gettext_lazy as _
import jwt
from .models import CustomUser
import json
from rest_framework.permissions import IsAuthenticated
import random
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from .models import OTP
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from datetime import datetime
import os

User = get_user_model()
verification_codes = {}

GOOGLE_CLIENT_IDS = [
    "256913505653-3p5rhao94l1k3cijelmv1i0vbbj49k5v.apps.googleusercontent.com",
    "256913505653-h6g3uv6vrdrje6qfih25ehbrbu4tm39o.apps.googleusercontent.com"
]

def extract_language(request):
    lang = request.headers.get("Accept-Language", "en")

    lang = lang.split(",")[0]
    lang = lang.split("-")[0]

    return lang.lower()

def generate_name(email, name=None):
    if name:
        return name.strip()
    return email.split("@")[0]

@api_view(['POST'])
@permission_classes([AllowAny])
def app_start(request):
    language = request.data.get("language") or extract_language(request)

    if request.user.is_authenticated:
        request.user.language = language
        request.user.save(update_fields=["language"])

    print(f"🌍 APP START LANGUAGE: {language}")

    return Response({
        "language": language,
        "is_authenticated": request.user.is_authenticated
    })

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh)
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    email = request.data.get("email")
    password = request.data.get("password")
    name = request.data.get("name")

    if not email or not password:
        return Response(
            {"error": "Email and password are required"},
            status=400
        )

    if User.objects.filter(email=email).exists():
        return Response(
            {"error": "User already exists"},
            status=400
        )

    final_name = generate_name(email, name)

    try:
        user = User.objects.create_user(
            email=email,
            password=password,
            name=final_name
        )

        user.username = final_name
        user.provider = "email"
        user.save()

        tokens = get_tokens_for_user(user)

        return Response({
            "access": tokens["access"],
            "refresh": tokens["refresh"]
        })

    except Exception as e:
        print("❌ REGISTER ERROR:", e)
        return Response(
            {"error": "Something went wrong"},
            status=500
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def logs(request):

    RESET = "\033[0m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"

    event = request.data.get("event", "")
    step = request.data.get("step", "")

    if "error" in event or "fail" in step:
        color = RED
    elif "tap" in event or "pressed" in step:
        color = YELLOW
    elif "success" in event:
        color = GREEN
    else:
        color = CYAN

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{color}📱 LOG START [{now}]{RESET}")

    log_lines = []
    log_lines.append(f"\n📱 LOG START [{now}]")

    for key, value in request.data.items():
        print(f"{color}{key}: {value}{RESET}")
        log_lines.append(f"{key}: {value}")

    print(f"{color}📱 LOG END{RESET}\n")
    log_lines.append("📱 LOG END\n")

    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, "app_logs.txt")

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            for line in log_lines:
                f.write(line + "\n")
    except Exception as e:
        print(f"{RED}❌ FILE LOG ERROR: {e}{RESET}")

    return Response({"ok": True})