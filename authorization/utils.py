import jwt
from datetime import datetime, timedelta,timezone
from django.conf import settings

def generate_token_verification(email,user_id):
 

    payload = {
        'email': email,
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(hours=24),
        'iat': datetime.now(timezone.utc)
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return token
    