from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from .models import Notification
from .serializers import NotificationSerializer


def create_and_send_notification(sender, receiver, message):
    """
    Creates notification in DB
    Sends realtime websocket notification
    """

    # ✅ Save to database
    notification = Notification.objects.create(
        sender=sender,
        receiver=receiver,
        message=message,
        is_read=False
    )

    # ✅ Serialize notification for frontend
    serializer = NotificationSerializer(notification)

    # ✅ Send realtime websocket notification
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"notify_{receiver.id}",
        {
            "type": "send_notification",  # must match consumer method
            "notification_data": serializer.data,
            "message": message,
            "is_notification": True
        }
    )

    return notification