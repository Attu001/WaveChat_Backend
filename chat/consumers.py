from channels.generic.websocket import AsyncWebsocketConsumer
import json

from channels.generic.websocket import AsyncWebsocketConsumer
import json

class PrivateChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user1 = self.scope["url_route"]["kwargs"]["user1"]
        self.user2 = self.scope["url_route"]["kwargs"]["user2"]

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
        message = data["message"]
        sender = data["sender"]

        # send chat message
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "sender": sender,
            }
        )

        # find receiver
        receiver = self.user2 if str(sender) == str(self.user1) else self.user1

        # send notification to receiver
        await self.channel_layer.group_send(
            f"notify_{receiver}",
            {
                "type": "send_notification",
                "message": message,
                "sender_id": sender,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))




class NotificationConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
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
        await self.send(text_data=json.dumps({
            "type": "notification",
            "message": event["message"],
            "sender_id": event["sender_id"]
        }))



    

