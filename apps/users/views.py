from django.contrib.auth import get_user_model
from google.oauth2 import id_token
from google.auth.transport.requests import Request
from django.utils.translation import gettext_lazy as _
import jwt
import re
import requests
from django.shortcuts import get_object_or_404
import uuid
from django.core.files.base import ContentFile
from rest_framework import status
from .models import UserSession
from django.contrib.auth.hashers import make_password
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils.translation import gettext as _
from .models import CustomUser
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
import random
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
import json
from threading import Thread
from .models import OTP
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from datetime import datetime
import os
from config.config import settings
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

    language = request.data.get("language") or extract_language(request)

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

    try:
        base_name = generate_name(email, name)

        user = User.objects.create(
            email=email,
            password=make_password(password),
            username=None,
            name=base_name,
            language=language,
            provider="email"
        )

        user.provider = "email"
        user.save()

        tokens = get_tokens_for_user(user)

        device_id = request.headers.get("Device-Id")

        print("📱 DEVICE ID:", device_id)

        UserSession.objects.create(
            user=user,
            device_id=device_id,
            refresh_token=tokens["refresh"]
        )

        return Response({
            "access": tokens["access"],
            "refresh": tokens["refresh"]
        })

    except Exception as e:
        print("❌ REGISTER ERROR:", str(e))

        return Response(
            {"error": "Something went wrong"},
            status=500
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get("email")
    password = request.data.get("password")

    print("🟡 LOGIN ATTEMPT:", email)

    if not email or not password:
        return Response(
            {"error": _("Email and password required")},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:

        print("❌ USER NOT FOUND")

        return Response(
            {"error": _("User not found")},
            status=status.HTTP_404_NOT_FOUND
        )

    if not user.check_password(password):
        print("❌ WRONG PASSWORD")

        return Response(
            {"error": _("Wrong password")},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not user.is_email_verified:
        print("❌ EMAIL NOT VERIFIED")

        return Response(
            {"error": _("Email not verified")},
            status=status.HTTP_403_FORBIDDEN
        )

    tokens = get_tokens_for_user(user)
    device_id = request.headers.get("Device-Id")

    print("📱 DEVICE ID:", device_id)

    UserSession.objects.create(
        user=user,
        device_id=device_id,
        refresh_token=tokens["refresh"]
    )

    print("🟢 LOGIN SUCCESS:", user.email)

    return Response({
        "access": tokens["access"],
        "refresh": tokens["refresh"]
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    email = request.data.get("email")
    password = request.data.get("password")

    print("🟡 RESET PASSWORD:", email)

    if not email or not password:
        return Response(
            {"error": _("Email and password required")},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:

        print("❌ USER NOT FOUND")

        return Response(
            {"error": _("User not found")},
            status=status.HTTP_404_NOT_FOUND
        )

    user.set_password(password)
    user.save()

    print("🟢 PASSWORD UPDATED:", user.email)

    return Response({
        "success": True
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):

    language = request.data.get("language", "en")
    token = request.data.get("id_token")
    print("📥 FULL REQUEST DATA:", request.data)
    print("🌍 LANGUAGE:", request.data.get("language"))

    if not token:
        return Response({"error": _("No token provided")}, status=400)

    try:
        idinfo = None

        for client_id in GOOGLE_CLIENT_IDS:
            try:
                idinfo = id_token.verify_oauth2_token(
                    token,
                    Request(),
                    client_id
                )
                break
            except ValueError:
                continue

        if not idinfo:
            return Response({"error": _("Invalid token")}, status=400)

        google_id = idinfo.get("sub")
        email = idinfo.get("email")

        if not email:
            return Response({"error": _("Email not found")}, status=400)

        raw_name = email.split("@")[0]
        name = re.sub(r'[^a-zA-Z0-9_]', '', raw_name).lower()

        if not name:
            name = "user"

        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "User already exists"},
                status=400
            )

        user = User.objects.create(
            email=email,
            username=None,
            name=name,
            provider="google",
            google_id=google_id,
            language=language,
        )

        tokens = get_tokens_for_user(user)
        device_id = request.headers.get("Device-Id")

        print("📱 DEVICE ID:", device_id)

        UserSession.objects.create(
            user=user,
            device_id=device_id,
            refresh_token=tokens["refresh"]
        )

        return Response({
            "access": tokens["access"],
            "refresh": tokens["refresh"]
        })

    except Exception as e:
        print("❌ GOOGLE AUTH ERROR:", str(e))
        return Response({"error": _("Something went wrong")}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def apple_auth(request):
    token = request.data.get("id_token")

    if not token:
        return Response({"error": _("No token provided")}, status=400)

    try:
        decoded = jwt.decode(token, options={"verify_signature": False})

        apple_id = decoded.get("sub")
        email = decoded.get("email")

        if not email:
            return Response({"error": _("Email not found")}, status=400)

        raw_name = email.split("@")[0]
        name = re.sub(r'[^a-zA-Z0-9_]', '', raw_name).lower()

        if not name:
            name = "user"

        user, created = User.objects.get_or_create(
            apple_id=apple_id,
            defaults={
                "email": email,
                "name": name,
                "username": None,
                "provider": "apple",
            }
        )
        if not created:
            if not user.email and email:
                user.email = email
                user.save()

        tokens = get_tokens_for_user(user)
        device_id = request.headers.get("Device-Id")

        print("📱 DEVICE ID:", device_id)

        UserSession.objects.create(
            user=user,
            device_id=device_id,
            refresh_token=tokens["refresh"]
        )

        return Response({
            "access": tokens["access"],
            "refresh": tokens["refresh"]
        })

    except Exception as e:
        print("❌ APPLE AUTH ERROR:", str(e))
        return Response({"error": _("Something went wrong")}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_code(request):
    email = request.data.get("email")
    code = request.data.get("code")

    otp = OTP.objects.filter(email=email).order_by("-created_at").first()

    if not otp:
        return Response({"error": "Code not found"}, status=400)

    if otp.is_verified:
        return Response({"error": "Code already used"}, status=400)

    if otp.is_expired():
        return Response({"error": "Code expired"}, status=400)

    if otp.code != code:
        otp.attempts += 1
        otp.save()
        return Response({"error": "Invalid code"}, status=400)

    otp.is_verified = True
    otp.save()

    user = User.objects.filter(email=email).first()
    if user:
        user.is_email_verified = True
        user.is_verified_for_reset = True
        user.save()

    return Response({"success": True})


@api_view(['POST'])
@permission_classes([AllowAny])
def send_code(request):
    email = request.data.get("email")

    if not email:
        return Response({"error": "Email required"}, status=400)

    OTP.objects.filter(email=email).delete()

    code = OTP.generate_code()

    otp = OTP.objects.create(
        email=email,
        code=code
    )

    print("📩 OTP:", code)

    send_verification_email(email, code)

    return Response({
        "message": "Code sent",
        "expires_in": 60
    })

def send_verification_email(email, code):
    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {os.getenv('RESEND_API_KEY')}",
            "Content-Type": "application/json",
        },
        json={
            "from": "noreply@trendix.app",
            "to": [email],
            "subject": "Verification Code",
            "html": f"<h2>Your code is: {code}</h2>"
        }
    )

    print("📨 RESEND STATUS:", response.status_code)
    print("📨 RESPONSE:", response.text)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def setup_profile(request):
    user = request.user

    username = request.data.get("username")
    avatar = request.FILES.get("avatar")
    language = request.data.get("language")

    print("🟡 SETUP PROFILE START")
    print("👤 USER:", user.id)
    print("👤 USERNAME:", username)

    if not username:
        return Response({"error": _("Username is required")}, status=400)

    if len(username) < 5:
        return Response({"error": _("Username too short")}, status=400)

    if len(username) > 15:
        return Response({"error": _("Username too long")}, status=400)

    if " " in username:
        return Response({"error": _("Username must not contain spaces")}, status=400)

    if not re.match(r'^[A-Za-z0-9_]+$', username):
        return Response({"error": _("Invalid username format")}, status=400)

    if User.objects.filter(username=username).exclude(id=user.id).exists():
        return Response({"error": _("Username already taken")}, status=400)

    user.username = username

    if avatar:

        if user.avatar:
            print("🗑 DELETING OLD AVATAR:", user.avatar.url)
            user.avatar.delete(save=False)

        import uuid
        ext = avatar.name.split('.')[-1]
        avatar.name = f"{user.id}_{uuid.uuid4()}.{ext}"

        user.avatar = avatar

        print("📸 NEW AVATAR SET:", avatar.name)

    if language:
        user.language = language

    user.is_profile_completed = True
    user.save()

    print("🟢 SETUP PROFILE SUCCESS")

    return Response({
        "success": True,
        "username": user.username,
        "avatar": user.avatar.url if user.avatar else None
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_me(request):
    user = request.user

    return Response({
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
        "cover": request.build_absolute_uri(user.cover.url) if user.cover else None,
        "is_email_verified": user.is_email_verified,
        "is_profile_completed": user.is_profile_completed,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_cover(request):
    print("📸 FILES:", request.FILES)

    image = request.FILES.get("cover")

    if not image:
        print("❌ NO IMAGE")
        return Response({"error": "No image"}, status=400)

    user = request.user

    if user.cover:
        user.cover.delete(save=False)

    user.cover = image
    user.save()

    print("✅ SAVED:", user.cover.url)

    return Response({
        "cover": user.cover.url
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    query = request.GET.get("q", "").strip()
    filter_type = request.GET.get("filter", "popular")

    users = CustomUser.objects.exclude(id=request.user.id)

    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(name__icontains=query)
        )

    if filter_type == "followers":
        users = users.order_by("-id")
    elif filter_type == "hashtags":
        users = users.order_by("-id")
    else:
        users = users.order_by("-id")

    users = users[:20]

    data = []

    for user in users:
        data.append({
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
        })

    return Response(data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_profile(request, user_id):
    user = get_object_or_404(User, id=user_id)

    data = {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
        "cover": request.build_absolute_uri(user.cover.url) if user.cover else None,
        "is_profile_completed": getattr(user, "is_profile_completed", False)
    }

    return Response(data)

@api_view(['POST'])
@permission_classes([AllowAny])
def logs(request):

    RESET = "\033[0m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"

    event = request.data.get("event", "")
    step = request.data.get("step", "")

    def get_level_and_color(event, step):
        if "error" in event or "fail" in step:
            return "ERROR", RED
        elif "success" in event:
            return "SUCCESS", GREEN
        elif "tap" in event or "pressed" in step:
            return "ACTION", YELLOW
        return "INFO", CYAN

    level, color = get_level_and_color(event, step)

    now = datetime.utcnow().isoformat()
    SENSITIVE = ["access", "refresh", "token", "email"]

    def sanitize(data):
        clean = {}
        for k, v in data.items():
            if any(s in k.lower() for s in SENSITIVE):
                clean[k] = "***"
            else:
                clean[k] = v
        return clean

    safe_data = sanitize(request.data)

    log = {
        "timestamp": now,
        "event": event,
        "step": step,
        "level": level,
        "data": safe_data,
        "device": request.data.get("device"),
        "ios": request.data.get("ios"),
        "app_version": request.data.get("app_version")
    }

    print(f"\n{color}📱 LOG START [{now}] [{level}]{RESET}")

    print(f"{MAGENTA}event: {event}{RESET}")
    print(f"{MAGENTA}step: {step}{RESET}")

    for key, value in safe_data.items():
        print(f"{color}{key}: {value}{RESET}")

    print(f"{color}📱 LOG END{RESET}\n")

    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, "app_logs.jsonl")

    def write():
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log) + "\n")
        except Exception as e:
            print(f"{RED}❌ FILE LOG ERROR: {e}{RESET}")

    Thread(target=write).start()

    return Response({"ok": True})

