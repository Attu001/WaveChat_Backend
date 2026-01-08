from django.urls import re_path
from .consumers import PrivateChatConsumer,NotificationConsumer

websocket_urlpatterns = [
    re_path(
        r"^ws/chat/(?P<user1>\d+)/(?P<user2>\d+)/$",
        PrivateChatConsumer.as_asgi(),
    ),
    re_path(
        r'ws/notifications/(?P<user_id>\d+)/$',
        NotificationConsumer.as_asgi()
    ),

]
