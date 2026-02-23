from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from .models import Notification


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

    # ✅ Send realtime websocket notification
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"notify_{receiver.id}",
        {
            "type": "send_notification",  # must match consumer method
            "message": message,
            "sender_id": sender.id,
            "created_at": notification.created_at.isoformat(),
        }
    )

    return notification