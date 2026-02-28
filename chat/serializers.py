from rest_framework import serializers
from .models import ChatRequest, Chat, Notification, Post
from authorization.models import User


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "profile_pic"]


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

class NotificationSerializer(serializers.ModelSerializer):
    sender = UserSimpleSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "sender",
            "message",
            "is_read",
            "created_at",
        ]


class PostSerializer(serializers.ModelSerializer):
    author = UserSimpleSerializer(read_only=True)
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "author",
            "content",
            "image_url",
            "like_count",
            "is_liked",
            "created_at",
        ]

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False