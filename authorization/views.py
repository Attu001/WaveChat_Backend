from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from authorization.models import User
@api_view(['POST'])
def register(request):
    name = request.data.get("name")
    email = request.data.get("email")
    password = request.data.get("password")

    if not name or not email or not password:
        return Response({"error": "All fields required"}, status=400)

    if User.objects.filter(email=email).exists():
        return Response({"error": "Email already registered"}, status=400)

    user = User.objects.create_user(email=email, name=name, password=password)

    return Response({"message": "User registered successfully"})

@api_view(['POST'])
def login_user(request):
    email = request.data.get("email")
    password = request.data.get("password")
    print(email,password)

    if not email or not password:
        return Response({"error": "Email and password required"}, status=400)

    user = authenticate(request, username=email, password=password)

    if user is None:
        print(user) 
        return Response({"error": "Invalid email or password"}, status=400)

    refresh = RefreshToken.for_user(user)

    return Response({
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user_id": user.id,
        "name": user.name,
        "email": user.email
    })
