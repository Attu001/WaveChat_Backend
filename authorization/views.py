from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from authorization.models import User
from django.core.mail import send_mail
from authorization.utils import generate_token_verification
from django.db import transaction
from django.shortcuts import get_object_or_404
import secrets
from .serializer import ProfileSerializer


@api_view(["POST"])
def register(request):
    name = request.data.get("name")
    email = request.data.get("email")
    password = request.data.get("password")

    if not name or not email or not password:
        return Response({"error": "All fields required"}, status=400)

    if User.objects.filter(email=email).exists():
        return Response({"error": "Email already registered"}, status=400)

    try:
        with transaction.atomic():
            token = secrets.token_urlsafe(32)

            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                name=name
            )
            
            user.token = token
            user.save()

            link = f"http://localhost:3000/verify?token={token}"

            send_mail(
                subject="Verify your Wavechat account",
                message=f"Please verify your account:\n{link}",
                from_email="atishchavan066@gmail.com",
                recipient_list=[email],
                fail_silently=False,
            )

        return Response(
            {"message": "User registered. Verification email sent."},
            status=201
        )

    except Exception as e:
        print("Registration Error:", e)
        return Response({"error": "Registration failed"}, status=500)

    


@api_view(["POST"])
def login_user(request):
    email = request.data.get("email")
    password = request.data.get("password")
    print(email, password)

    if not email or not password:
        return Response({"error": "Email and password required"}, status=400)

    user = authenticate(request, username=email, password=password)

    if user is None:
        print(user)
        return Response({"error": "Invalid email or password"}, status=400)

    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
        }
    )


@api_view(["GET"])
def verify_email(request):
    token = request.query_params.get("token") 
    try:
        user = User.objects.get(token=token)
        user.is_verified = True
        user.verification_token = None
        user.save()

        return Response({"message": "Email verified successfully"})
    except User.DoesNotExist:
        return Response({"error": "Invalid token"}, status=400)
    

@api_view(["GET"])
def get_all_users(request):
    users=User.objects.all().values(
        "id",
        "name",
        "email"
    )
    
    return Response(users)


@api_view(["POST"])
def get_profile(request):
    id = request.data.get("id")

    user = User.objects.filter(id=id).first()
    if not user:
        return Response({"error": "User not found"}, status=404)

    serializer = ProfileSerializer(user)
    return Response(serializer.data, status=200)
    
    
    

