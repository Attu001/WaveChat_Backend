from channels.generic.websocket import AsyncWebsocketConsumer
import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Chat, Message
from authorization.utils import get_or_create_private_chat
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import AnonymousUser

User = get_user_model()


class PrivateChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Get token from query string
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]
        
        if not token:
            await self.close()
            return
        
        # Validate token and get user
        user = await get_user_from_token(token)
        if not user or isinstance(user, AnonymousUser):
            await self.close()
            return
        
        self.scope["user"] = user
        self.user1 = int(self.scope["url_route"]["kwargs"]["user1"])
        self.user2 = int(self.scope["url_route"]["kwargs"]["user2"])

        # Verify the authenticated user is one of the chat participants
        if user.id not in [self.user1, self.user2]:
            await self.close()
            return

        users = sorted([self.user1, self.user2])
        self.room_group_name = f"private_{users[0]}_{users[1]}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        text = data["message"]

        sender = self.scope["user"]
        if not sender.is_authenticated:
            return

        user1 = await get_user(self.user1)
        user2 = await get_user(self.user2)

        # ✅ Proper async DB call
        chat = await database_sync_to_async(get_or_create_private_chat)(user1, user2)

        message_obj = await save_message(chat, sender, text)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message_obj.text,
                "sender": sender.id,
                "chat_id": chat.id,
                "created_at": message_obj.created_at.isoformat()
            }
        )

        receiver_id = user2.id if sender.id == user1.id else user1.id
        await self.channel_layer.group_send(
            f"notify_{receiver_id}",
            {
                "type": "send_notification",
                "message": text,
                "sender_id": sender.id,
                "is_chat_message": True
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))


class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        # Get token from query string
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]
        
        if not token:
            await self.close()
            return
        
        # Validate token and get user
        user = await get_user_from_token(token)
        if not user or isinstance(user, AnonymousUser):
            await self.close()
            return
        
        self.scope["user"] = user
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]

        # Verify the authenticated user matches the requested user_id
        if user.id != int(self.user_id):
            await self.close()
            return

        self.room_group_name = f"notify_{self.user_id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    

    async def send_notification(self, event):
        payload = {
            "type": "notification"
        }
        if event.get("is_notification"):
            payload["is_notification"] = True
            payload["notification"] = event.get("notification_data")
            payload["message"] = event.get("message")
        elif event.get("is_chat_message"):
            payload["is_chat_message"] = True
            payload["message"] = event.get("message")
            payload["sender_id"] = event.get("sender_id")

        await self.send(text_data=json.dumps(payload))


@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

@database_sync_to_async
def get_user_from_token(token):
    try:
        access_token = AccessToken(token)
        user_id = access_token["user_id"]
        return User.objects.get(id=user_id)
    except Exception:
        return AnonymousUser()


@database_sync_to_async
def save_message(chat, sender, text):
    return Message.objects.create(
        chat=chat,
        sender=sender,
        text=text
    )
