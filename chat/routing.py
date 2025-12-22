from django.urls import re_path
from .consumers import PrivateChatConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<user1>\d+)/(?P<user2>\d)/$", PrivateChatConsumer.as_asgi()),
]
