from channels.generic.websocket import AsyncWebsocketConsumer
import json

class PrivateChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user1 = self.scope["url_route"]["kwargs"]["user1"]
        user2 = self.scope["url_route"]["kwargs"]["user2"]

        # normalize group name (IMPORTANT)
        users = sorted([user1, user2])
        self.room_group_name = f"private_{users[0]}_{users[1]}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        await self.send(text_data=json.dumps({
            "system": "Connected to private chat"
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data["message"]
        sender = data.get("sender")

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "sender": sender,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "sender": event["sender"],
        }))
