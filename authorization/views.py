from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from authorization.models import User
from django.core.mail import send_mail
from authorization.utils import generate_token_verification
from django.db import transaction
from django.shortcuts import get_object_or_404
import secrets
import threading
from .serializer import ProfileSerializer, ProfileUpdateSerializer
from threading import Thread
from rest_framework import status
from django.conf import settings
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated









@api_view(["POST"])
def register(request):
    name = request.data.get("name")
    email = request.data.get("email")
    password = request.data.get("password")

    # 1️⃣ Validate input
    if not name or not email or not password:
        return Response({"error": "All fields required"}, status=400)

    # 2️⃣ STOP immediately if email exists
    if User.objects.filter(email=email).exists():
        return Response({"error": "Email already registered"}, status=400)

    try:
        # 3️⃣ Create user safely
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

        # # 4️⃣ Send email ONLY after success
        # frontend_url = "https://wavechat-snowy.vercel.app"
        # verify_link = f"{frontend_url}/verify?token={token}"

        # send_verification_email(user.email, token)


        return Response(
            {"message": "User registered."},
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
    
    # if not user.is_verified:
    #     return Response({"error":"Please verify Your email first!"},status=403)

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
@permission_classes([IsAuthenticated])
def get_all_users(request):
    users = User.objects.exclude(id=request.user.id).values(
        "id",
        "name",
        "email"
    )
    return Response(users)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_profile(request):
    serializer = ProfileSerializer(request.user)
    return Response(serializer.data, status=200)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_profile(request,user_id):
    try:
        user =User.objects.get(id=user_id)
        serializer=ProfileSerializer(user)
        return Response(serializer.data)
    except User.DoesNotExist:
        return Response({"error":"User not Found"},status=404)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        profile_serializer = ProfileSerializer(request.user)
        return Response(profile_serializer.data, status=200)
    return Response(serializer.errors, status=400)


    
    

    
    
    

