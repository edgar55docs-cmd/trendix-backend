from django.contrib.auth import get_user_model
from google.oauth2 import id_token
from google.auth.transport import requests
from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import AllowAny
import jwt
from .models import CustomUser
import json
import random
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from .models import OTP
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()
verification_codes = {}

GOOGLE_CLIENT_IDS = [
    "256913505653-3p5rhao94l1k3cijelmv1i0vbbj49k5v.apps.googleusercontent.com",
    "256913505653-h6g3uv6vrdrje6qfih25ehbrbu4tm39o.apps.googleusercontent.com"
]

@api_view(['GET'])
@permission_classes([AllowAny])
def app_start(request):
    language = request.headers.get("Accept-Language", "en")

    language = language.split(",")[0]
    language = language.split("-")[0]

    return Response({
        "received_language": language
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):

    token = request.data.get("id_token")

    if not token:
        return Response({"error": _("No token provided")}, status=400)

    try:
        idinfo = None

        for client_id in GOOGLE_CLIENT_IDS:
            try:
                idinfo = id_token.verify_oauth2_token(
                    token,
                    requests.Request(),
                    client_id
                )
                break
            except ValueError:
                continue

        if not idinfo:
            return Response({"error": _("Invalid token")}, status=400)

        google_id = idinfo.get("sub")
        email = idinfo.get("email")

        if not google_id:
            return Response({"error": _("No google id")}, status=400)

        name = idinfo.get("name") or (email.split("@")[0] if email else None)

        user, created = User.objects.get_or_create(
            google_id=google_id,
            defaults={
                "email": email,
                "name": name,
                "provider": "google",
                "is_email_verified": True
            }
        )

        if not created:
            updated = False

            if not user.name and name:
                user.name = name
                updated = True

            if not user.email and email:
                user.email = email
                updated = True

            if updated:
                user.save()

        return Response({
            "success": True,
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "provider": "google",
            "created": created
        })

    except ValueError:
        return Response({"error": _("Invalid token")}, status=400)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def setup_profile(request):

    username = request.data.get("username")
    avatar = request.FILES.get("avatar")
    cover = request.FILES.get("cover")
    user_id = request.data.get("user_id")

    if not user_id:
        return Response({"error": _("No user id")}, status=400)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": _("User not found")}, status=404)

    if username:
        user.username = username

    if avatar:
        user.avatar = avatar

    if cover:
        user.cover = cover

    user.save()

    avatar_url = user.avatar.url if user.avatar else None
    cover_url = user.cover.url if user.cover else None

    return Response({
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "avatar": request.build_absolute_uri(avatar_url) if avatar_url else None,
        "cover": request.build_absolute_uri(cover_url) if cover_url else None,
        "email": user.email
    })

@api_view(["GET", "PATCH"])
@permission_classes([AllowAny])
def me(request):

    user_id = request.headers.get("X-User-Id")

    if not user_id:
        return Response({"error": _("No user id")}, status=400)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": _("User not found")}, status=404)

    if request.method == "PATCH":

        name = request.data.get("name")
        username = request.data.get("username")

        if name is not None:
            user.name = name

        if username is not None:
            user.username = username

        user.save()

    return Response({
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "avatar": request.build_absolute_uri(
            user.avatar.url
        ) if user.avatar else None,
        "cover": request.build_absolute_uri(
            user.cover.url
        ) if user.cover else None,
        "email": user.email
    })

@api_view(["GET"])
@permission_classes([AllowAny])
def check_username(request):

    username = request.GET.get("username")

    if not username:
        return Response({"error": "No username"}, status=400)

    exists = User.objects.filter(username__iexact=username).exists()

    return Response({
        "available": not exists
    })


from rest_framework.permissions import AllowAny

@api_view(["GET"])
@permission_classes([AllowAny])
def check_name(request):

    name = request.GET.get("name")
    current_user_id = request.headers.get("X-User-Id")

    if not name:
        return Response({"error": "No name"}, status=400)

    query = User.objects.filter(name__iexact=name)

    if current_user_id:
        query = query.exclude(id=int(current_user_id))

    exists = query.exists()

    print("👤 HEADER USER ID:", current_user_id)
    print("📊 EXISTS:", exists)

    return Response({
        "available": not exists
    })

@api_view(["GET"])
@permission_classes([AllowAny])
def search_users(request):

    query = request.GET.get("q", "")
    current_user_id = request.headers.get("X-User-Id")

    if not query:
        return Response([], status=200)

    users = User.objects.filter(
        username__icontains=query
    )

    if current_user_id:
        users = users.exclude(id=current_user_id)

    data = []

    for user in users:
        data.append({
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "avatar": request.build_absolute_uri(
                user.avatar.url
            ) if user.avatar else None,
        })

    return Response(data)

@api_view(["GET"])
@permission_classes([AllowAny])
def get_user_by_id(request, user_id):

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": _("User not found")}, status=404)

    return Response({
        "id": user.id,
        "name": user.name,
        "username": user.username,

        "avatar": request.build_absolute_uri(
            user.avatar.url
        ) if user.avatar else None,

        "cover": request.build_absolute_uri(
            user.cover.url
        ) if user.cover else None,

        "email": user.email
    })

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }

@api_view(['POST'])
def apple_login(request):
    token = request.data.get("id_token")

    if not token:
        return Response({"error": "No token"}, status=400)

    try:
        decoded = jwt.decode(token, options={"verify_signature": False})

        apple_id = decoded.get("sub")
        email = decoded.get("email")

        if not apple_id:
            return Response({"error": "No apple_id"}, status=400)

        user, _ = CustomUser.objects.get_or_create(
            apple_id=apple_id,
            defaults={
                "email": email,
                "provider": "apple",
                "is_email_verified": True
            }
        )

        if not user.email and email:
            user.email = email
            user.save()

        tokens = get_tokens_for_user(user)

        return Response({
            "user_id": user.id,
            "email": user.email,
            "access": tokens["access"],
            "refresh": tokens["refresh"]
        })

    except Exception as e:
        return Response({"error": str(e)}, status=400)

@csrf_exempt
def send_verification_code(request):
    if request.method == "POST":

        data = json.loads(request.body)
        email = data.get("email")

        if not email:
            return JsonResponse({"error": "Email required"}, status=400)

        last_otp = OTP.objects.filter(email=email).order_by('-created_at').first()

        if last_otp and timezone.now() - last_otp.created_at < timedelta(seconds=30):
            return JsonResponse({"error": "Wait before requesting again"}, status=429)

        OTP.objects.filter(email=email).delete()

        code = str(random.randint(100000, 999999))

        otp = OTP.objects.create(
            email=email,
            code=code
        )

        send_mail(
            "Trendix Verification Code",
            f"Your code is: {code}",
            "noreplytrendix@gmail.com",
            [email],
            fail_silently=False,
        )

        return JsonResponse({"success": True})


@csrf_exempt
def verify_code(request):
    if request.method == "POST":

        data = json.loads(request.body)
        email = data.get("email")
        code = data.get("code")

        if not email or not code:
            return JsonResponse({"error": "Invalid data"}, status=400)

        try:
            otp = OTP.objects.get(email=email, code=code)

            if timezone.now() - otp.created_at > timedelta(minutes=5):
                otp.delete()
                return JsonResponse({"error": "Code expired"}, status=400)

            otp.is_verified = True
            otp.save()

            base_name = email.split("@")[0]

            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    "name": base_name,
                    "provider": "email",
                    "is_email_verified": True
                }
            )

            if not created:
                user.is_email_verified = True
                if not user.name:
                    user.name = base_name
                user.save()

            print("✅ USER CREATED:", user.id, user.email)

            refresh = RefreshToken.for_user(user)

            return JsonResponse({
                "success": True,
                "user_id": user.id,
                "email": user.email,
                "name": user.name,
                "access": str(refresh.access_token),
                "refresh": str(refresh)
            })

        except OTP.DoesNotExist:
            return JsonResponse({"error": "Invalid code"}, status=400)


@csrf_exempt
def app_log(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            log = data.get("log")
            user_id = data.get("user_id")

            print("\n📱 APP LOG")
            print("👤 USER:", user_id)
            print("📝 LOG:", log)
            print("----------\n")

            return JsonResponse({"success": True})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)