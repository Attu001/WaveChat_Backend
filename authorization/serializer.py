from rest_framework import serializers
from .models import User


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "bio", "phone", "profile_pic"]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name", "bio", "phone", "profile_pic"]
        extra_kwargs = {
            "name": {"required": False},
            "bio": {"required": False},
            "phone": {"required": False},
            "profile_pic": {"required": False},
        }