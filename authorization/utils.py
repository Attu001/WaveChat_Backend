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
        .first()
    )

    if chat:
        return chat

    chat = Chat.objects.create(is_group=False)
    chat.participants.add(user1, user2)
    return chat

# Private users: these users can only see each other
PRIVATE_EMAILS = {"divya@gmail.com", "atish@gmail.com"}

def apply_privacy_filter(request_user, queryset, email_field='email'):
    """
    Applies privacy filtering to a queryset based on the requesting user.
    - Private users only see other private users.
    - Regular users never see private users.
    """
    if not request_user.is_authenticated:
        # For unauthenticated requests, hide all private users
        return queryset.exclude(**{f"{email_field}__in": PRIVATE_EMAILS})

    # Normalize to lowercase for reliable comparison
    user_email = request_user.email.lower().strip()
    
    if user_email in PRIVATE_EMAILS:
        # Private user → only show other private users (including self if in list)
        return queryset.filter(**{f"{email_field}__in": PRIVATE_EMAILS})
    else:
        # Regular user → hide all private users
        return queryset.exclude(**{f"{email_field}__in": PRIVATE_EMAILS})

    