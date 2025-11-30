import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get room_id from the URL
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]

        # Create group name for room
        self.room_group_name = f"chat_{self.room_id}"

        # Add this connection to the room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Accept the WebSocket connection
        await self.accept()

    async def disconnect(self, close_code):
        # Remove connection from the room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Convert JSON string to Python dict
        data = json.loads(text_data)

        # Broadcast message to entire room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": data["message"],
                "sender": data["sender"],
                "receiver": data["receiver"],
            }
        )

    async def chat_message(self, event):
        # Send event back to WebSocket frontend
        await self.send(text_data=json.dumps(event))
