from django.contrib.auth import get_user_model
from google.oauth2 import id_token
from google.auth.transport.requests import Request
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

        # 🔐 verify token բոլոր client-ներով
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

        # 📦 տվյալներ Google-ից
        google_id = idinfo.get("sub")
        email = idinfo.get("email")
        name = idinfo.get("name") or (email.split("@")[0] if email else None)

        if not google_id:
            return Response({"error": _("No google id")}, status=400)

        # 🔥 ՀԻՄՆԱԿԱՆ LOGIC

        user = None

        # 1️⃣ փնտրում ենք ըստ EMAIL
        if email:
            user = User.objects.filter(email=email).first()

        # 2️⃣ եթե ՉԿԱ → CREATE
        try:
            if not user:
                user = User.objects.create(
                    email=email,
                    name=name,
                    google_id=google_id,
                    provider="google",
                    is_email_verified=True
                )
                created = True
            else:
                created = False

        except Exception:
            # եթե duplicate եղավ → վերցնում ենք արդեն եղած user-ը
            user = User.objects.filter(email=email).first()
            created = False

        # 3️⃣ եթե ԿԱ → UPDATE / LOGIN
        else:
            created = False

            if not user.google_id:
                user.google_id = google_id

            if not user.name and name:
                user.name = name

            user.provider = "google"
            user.is_email_verified = True

            user.save()

        # 🎯 RESPONSE
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

        import traceback

        print("🔥 GOOGLE ERROR:")

        traceback.print_exc()

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
@permission_classes([AllowAny])
def apple_login(request):
    print("\n🍏🍏🍏 APPLE LOGIN START 🍏🍏🍏")
    print("📥 RAW DATA:", request.data)

    token = request.data.get("id_token")

    if not token:
        print("❌ ERROR: No token received")
        return Response({"error": "No token"}, status=400)

    print("🟡 Token received length:", len(token))
    print("🟡 Token preview:", token[:30], "...")

    try:
        print("🔍 Decoding token...")

        decoded = jwt.decode(token, options={"verify_signature": False})

        print("🟢 TOKEN DECODED SUCCESS")
        print("📦 Decoded payload:", decoded)

        apple_id = decoded.get("sub")
        email = decoded.get("email")

        print("🟡 Apple ID:", apple_id)
        print("🟡 Email:", email)

        if not apple_id:
            print("❌ ERROR: No apple_id in token")
            return Response({"error": "No apple_id"}, status=400)

        # 🔥 username ստացում email-ից
        username = None

        if email:
            base_username = email.split("@")[0]
            username = base_username

            # 🔥 unique username սարքել
            import random
            while CustomUser.objects.filter(username=username).exists():
                username = f"{base_username}{random.randint(1000,9999)}"

        print("🟡 Generated username:", username)

        print("🔎 Searching or creating user...")

        user, created = CustomUser.objects.get_or_create(
            apple_id=apple_id,
            defaults={
                "email": email,
                "username": username,
                "provider": "apple",
                "is_email_verified": True
            }
        )

        if created:
            print("🆕 NEW USER CREATED:", user.id)
            print("🆕 USERNAME:", username)
        else:
            print("👤 EXISTING USER:", user.id)

        # 🔥 եթե հին user է ու email չկա → լրացնենք
        if not user.email and email:
            print("✏️ Updating user email...")
            user.email = email
            user.save()

        print("🔑 Generating tokens...")

        tokens = get_tokens_for_user(user)

        print("🟢 TOKENS GENERATED")

        response_data = {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,  # 🔥 ավելացրեցինք
            "access": tokens["access"],
            "refresh": tokens["refresh"]
        }

        print("📤 RESPONSE:", response_data)
        print("🍏🍏🍏 APPLE LOGIN SUCCESS 🍏🍏🍏\n")

        return Response(response_data)

    except Exception as e:
        print("🔥🔥🔥 APPLE LOGIN ERROR 🔥🔥🔥")
        print("❌ ERROR:", str(e))
        print("📛 TYPE:", type(e))
        print("🍏🍏🍏 END WITH ERROR 🍏🍏🍏\n")

        return Response({"error": str(e)}, status=400)


@csrf_exempt
def send_verification_code(request):

    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get("email")

        if not email:
            return JsonResponse({"error": "Email required"}, status=400)

        last_otp = OTP.objects.filter(email=email).order_by('-created_at').first()

        if last_otp and timezone.now() - last_otp.created_at < timedelta(seconds=30):
            return JsonResponse({"error": "Wait before requesting again"}, status=429)

        OTP.objects.filter(email=email).delete()

        code = str(random.randint(100000, 999999))

        OTP.objects.create(email=email, code=code)

        send_mail(
            "Trendix Verification Code",
            f"Your code is: {code}",
            "noreplytrendix@gmail.com",
            [email],
            fail_silently=False,
        )

        return JsonResponse({"success": True})

    except Exception as e:
        print("💥 ERROR:", str(e))
        return JsonResponse({"error": "Server error"}, status=500)


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

    print(f"\n{color}📱 LOG START{RESET}")

    for key, value in request.data.items():
        print(f"{color}{key}: {value}{RESET}")

    print(f"{color}📱 LOG END{RESET}\n")

    return Response({"ok": True})