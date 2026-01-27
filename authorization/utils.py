import jwt
from datetime import datetime, timedelta,timezone
from django.conf import settings
from chat.models import Chat

def generate_token_verification(email,user_id):

    payload = {
        'email': email,
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(hours=24),
        'iat': datetime.now(timezone.utc)
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return token

from django.db.models import Count

def get_or_create_private_chat(user1, user2):
    chat = (
        Chat.objects
        .filter(is_group=False, participants=user1)
        .filter(participants=user2)
        .annotate(count=Count("participants"))
        .filter(count=2)
        .first()
    )

    if chat:
        return chat

    chat = Chat.objects.create(is_group=False)
    chat.participants.add(user1, user2)
    return chat

    