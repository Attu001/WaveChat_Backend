from rest_framework import serializers
from .models import ChatRequest, Chat
from authorization.models import User


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email"]


class ChatRequestSerializer(serializers.ModelSerializer):
    sender = UserSimpleSerializer(read_only=True)
    receiver = UserSimpleSerializer(read_only=True)

    class Meta:
        model = ChatRequest
        fields = [
            "id",
            "sender",
            "receiver",
            "status",
            "created_at",
        ]


class ChatSerializer(serializers.ModelSerializer):
    participants = UserSimpleSerializer(many=True, read_only=True)

    class Meta:
        model = Chat
        fields = [
            "id",
            "participants",
            "is_group",
            "created_at",
        ]
