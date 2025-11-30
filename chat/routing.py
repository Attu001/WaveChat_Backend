from django.urls import re_path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/room/(?P<room_id>[\w-]+)/$", ChatConsumer.as_asgi()),
]
