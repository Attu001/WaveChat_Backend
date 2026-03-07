from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from authorization.models import User
from authorization.utils import generate_token_verification, get_or_create_private_chat, apply_privacy_filter
from django.shortcuts import get_object_or_404
from rest_framework import status
from django.conf import settings
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import ChatRequest, Chat, Message
from .serializers import ChatRequestSerializer
from django.db.models import Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .utils import create_and_send_notification
from .models import Notification
from .serializers import NotificationSerializer


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_chat_request(request, user_id):
    sender = request.user
    receiver = get_object_or_404(User, id=user_id)

    if receiver == sender:
        return Response({"error": "Cannot send request to yourself"}, status=400)

    # 1. CHECK IF THEY ALREADY SENT US A REQUEST
    incoming_request = ChatRequest.objects.filter(
        sender=receiver,
        receiver=sender
    ).first()

    if incoming_request:
        if incoming_request.status == ChatRequest.PENDING:
            # Tell user to accept the incoming one
            return Response({
                "error": "You already have a pending request from this user. Please accept it.",
                "status": "PENDING_RECEIVED",
                "request_id": incoming_request.id
            }, status=400)
        
        if incoming_request.status == ChatRequest.ACCEPTED:
            return Response({"error": "You are already friends", "status": "ACCEPTED"}, status=400)

    # 2. CHECK OUR EXISTING REQUEST TO THEM
    outgoing_request = ChatRequest.objects.filter(
        sender=sender,
        receiver=receiver
    ).first()

    if outgoing_request:
        if outgoing_request.status == ChatRequest.PENDING:
            return Response({"error": "Request already exists and is pending", "status": "PENDING_SENT"}, status=400)
        
        if outgoing_request.status == ChatRequest.ACCEPTED:
            return Response({"error": "You are already friends", "status": "ACCEPTED"}, status=400)
            
        # If REJECTED, reset to PENDING and notify
        if outgoing_request.status == ChatRequest.REJECTED:
            outgoing_request.status = ChatRequest.PENDING
            outgoing_request.save()
            create_and_send_notification(
                sender=sender,
                receiver=receiver,
                message=f"{sender.name} sent you a chat request."
            )
            return Response({"message": "Chat request resent", "status": "PENDING_SENT"})

    # 3. CREATE NEW REQUEST
    ChatRequest.objects.create(sender=sender, receiver=receiver)
    create_and_send_notification(
        sender=sender,
        receiver=receiver,
        message=f"{sender.name} has sent you a chat request."
    )
    
    return Response({"message": "Chat request sent", "status": "PENDING_SENT"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pending_requests(request):
    requests = ChatRequest.objects.filter(
        receiver=request.user,
        status=ChatRequest.PENDING
    ).select_related("sender")
    
    # Privacy filter: Hide private users from public users, and vice versa
    requests = apply_privacy_filter(request.user, requests, email_field='sender__email')
    
    serializer = ChatRequestSerializer(requests, many=True)
    return Response(serializer.data)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def accepted_friends(request):
    user = request.user

    chats = Chat.objects.filter(
        is_group=False,
        participants=user
    ).prefetch_related("participants")

    friends = []

    for chat in chats:
        other_user = chat.participants.exclude(id=user.id).first()
        if not other_user: continue

        # Privacy Check
        if not apply_privacy_filter(user, User.objects.filter(id=other_user.id)).exists():
            continue

        friends.append({
            "chat_id": chat.id,
            "id": other_user.id,
            "name": other_user.name,
            "email": other_user.email,
            "profile_pic": other_user.profile_pic,
        })

    return Response(friends)




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reject_request(request, request_id):
    chat_request = get_object_or_404(
        ChatRequest,
        id=request_id,
        receiver=request.user
    )
    chat_request.status = ChatRequest.REJECTED
    chat_request.save()

    create_and_send_notification(
    sender=request.user,
    receiver=chat_request.sender,
    message=f"{request.user.name} has rejected your chat request."
)
    return Response({"message": "Request rejected"})




@api_view(["GET"])
@permission_classes([IsAuthenticated])
def users_with_status(request):
    """
    Returns a list of all users with their relationship status relative to the current user.
    Statuses: NONE, PENDING_SENT, PENDING_RECEIVED, ACCEPTED, REJECTED
    """
    current_user = request.user

    # 1. Fetch all visible users based on privacy
    all_users = User.objects.exclude(id=current_user.id)
    filtered_users = apply_privacy_filter(current_user, all_users)
    user_list = list(filtered_users.values("id", "name", "email", "profile_pic"))

    # 2. Get all relevant chat requests involving current user
    # We fetch PENDING, REJECTED, and ACCEPTED to be comprehensive
    requests_q = ChatRequest.objects.filter(
        Q(sender=current_user) | Q(receiver=current_user)
    )
    
    # 3. Get all private chats to confirm friendship status
    accepted_chats = Chat.objects.filter(
        is_group=False,
        participants=current_user
    ).prefetch_related("participants")
    
    friend_ids = set()
    for c in accepted_chats:
        other = c.participants.exclude(id=current_user.id).first()
        if other:
            friend_ids.add(other.id)

    # 4. Map requests to dictionaries for O(1) lookup
    sent_requests = {}      # receiver_id -> status
    received_requests = {}  # sender_id -> (status, request_id)

    for req in requests_q:
        if req.sender_id == current_user.id:
            sent_requests[req.receiver_id] = req.status
        else:
            received_requests[req.sender_id] = (req.status, req.id)

    # 5. Build final data list
    data = []
    for user in user_list:
        uid = user["id"]
        status_value = "NONE"
        request_id = None

        # Logic Priority: 
        # 1. Are they friends? (ACCEPTED)
        # 2. Did they send us a request? (PENDING_RECEIVED)
        # 3. Did we send them a request? (PENDING_SENT)
        # 4. Was a request rejected? (REJECTED_SENT / REJECTED_RECEIVED -> mapped to NONE for resending)

        if uid in friend_ids:
            status_value = "ACCEPTED"
        elif uid in received_requests:
            req_status, req_id = received_requests[uid]
            if req_status == ChatRequest.PENDING:
                status_value = "PENDING_RECEIVED"
                request_id = req_id
            elif req_status == ChatRequest.REJECTED:
                status_value = "NONE" # Allow them to send a fresh request if previously rejected
        elif uid in sent_requests:
            req_status = sent_requests[uid]
            if req_status == ChatRequest.PENDING:
                status_value = "PENDING_SENT"
            elif req_status == ChatRequest.REJECTED:
                status_value = "NONE" # Allow them to retry if we were rejected
        
        data.append({
            **user,
            "status": status_value,
            "request_id": request_id,
        })

    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_request(request, request_id):
    # get only PENDING request sent to current user
    chat_request = get_object_or_404(
        ChatRequest,
        id=request_id,
        receiver=request.user,
        status=ChatRequest.PENDING
    )

    # mark as accepted
    chat_request.status = ChatRequest.ACCEPTED
    chat_request.save()

    # check if private chat already exists between users
    existing_chat = Chat.objects.filter(
        is_group=False,
        participants=chat_request.sender
    ).filter(
        participants=chat_request.receiver
    ).first()

    # create chat only if not exists
    if existing_chat:
        chat = existing_chat
    else:
        chat = Chat.objects.create(
            is_group=False   # optional if you added OneToOneField
        )
        chat.participants.add(chat_request.sender, chat_request.receiver)
    
    create_and_send_notification(
    sender=request.user,
    receiver=chat_request.sender,
    message=f"{request.user.name} has accepted your chat request."
)
    return Response({
        "message": "Request accepted",
        "chat_id": chat.id
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_notifications(request):
    notifications = Notification.objects.filter(receiver=request.user).order_by("-created_at")
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def chat_history(request, other_user_id):
    other_user = get_object_or_404(User, id=other_user_id)

    # Find existing private chat between the two users
    chat = (
        Chat.objects
        .filter(is_group=False, participants=request.user)
        .filter(participants=other_user)
        .first()
    )

    if not chat:
        return Response([])  # No chat exists yet

    messages = chat.messages.order_by("created_at").values(
        "id", "text", "sender_id", "created_at"
    )

    data = [
        {
            "message": msg["text"],
            "sender": msg["sender_id"],
            "timestamp": msg["created_at"].isoformat(),
        }
        for msg in messages
    ]

    return Response(data)


# ===== Posts =====

from .models import Post
from .serializers import PostSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_posts(request):
    posts = Post.objects.all().select_related("author").prefetch_related("likes")
    
    # Apply privacy filter to posts based on author's email
    posts = apply_privacy_filter(request.user, posts, email_field='author__email')
    
    serializer = PostSerializer(posts, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_post(request):
    content = request.data.get("content", "").strip()
    image_url = request.data.get("image_url", "")

    if not content:
        return Response({"error": "Content is required"}, status=400)

    post = Post.objects.create(
        author=request.user,
        content=content,
        image_url=image_url,
    )

    serializer = PostSerializer(post, context={"request": request})
    return Response(serializer.data, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True

    return Response({
        "liked": liked,
        "like_count": post.likes.count(),
    })


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if post.author != request.user:
        return Response({"error": "Not authorized"}, status=403)

    post.delete()
    return Response({"message": "Post deleted"}, status=200)


# ===== Pexels Explore Feed =====

import requests as http_requests
import random

PEXELS_API_KEY = "FjhCPTfPzgGZasx3hSslBvVqOJZ3GubjVTQ3LioeNRfQxIREaeHzGkYe"

FAKE_AUTHORS = [
    {"name": "Sophia Chen", "email": "sophia@wave.io"},
    {"name": "Marcus Rivera", "email": "marcus@wave.io"},
    {"name": "Aisha Patel", "email": "aisha@wave.io"},
    {"name": "Liam O'Brien", "email": "liam@wave.io"},
    {"name": "Yuki Tanaka", "email": "yuki@wave.io"},
    {"name": "Elena Vasquez", "email": "elena@wave.io"},
    {"name": "David Kim", "email": "david@wave.io"},
    {"name": "Zara Mitchell", "email": "zara@wave.io"},
]

PHOTO_CAPTIONS = [
    "Just caught this beautiful moment ✨",
    "Nature never stops amazing me 🌿",
    "Vibes are immaculate today 🔥",
    "Living in the moment 💫",
    "This view though... 😍",
    "Weekend mood 🌅",
    "Can't stop staring at this 📸",
    "Pure magic ✨🎨",
    "Adventures await 🗺️",
    "Golden hour hits different 🌞",
    "Some moments are worth sharing 💜",
    "Peaceful mornings ☕",
]

VIDEO_CAPTIONS = [
    "Check out this amazing clip! 🎬",
    "Motion in every frame 🎥",
    "This is so satisfying to watch 😌",
    "Captured something special today 🌟",
    "The world in motion 🌊",
    "Can't stop replaying this ▶️",
]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def explore_feed(request):
    page = int(request.query_params.get("page", 1))
    per_page = int(request.query_params.get("per_page", 10))

    headers = {"Authorization": PEXELS_API_KEY}
    feed_items = []

    try:
        # Fetch curated photos
        photo_res = http_requests.get(
            f"https://api.pexels.com/v1/curated?page={page}&per_page={per_page}",
            headers=headers,
            timeout=8,
        )

        if photo_res.status_code == 200:
            photos = photo_res.json().get("photos", [])
            for i, photo in enumerate(photos):
                author = random.choice(FAKE_AUTHORS)
                feed_items.append({
                    "id": f"photo_{photo['id']}",
                    "type": "photo",
                    "author": {
                        "id": photo["photographer_id"],
                        "name": photo["photographer"],
                        "email": author["email"],
                        "profile_pic": None,
                    },
                    "content": random.choice(PHOTO_CAPTIONS),
                    "media": {
                        "type": "photo",
                        "url": photo["src"]["large2x"],
                        "thumbnail": photo["src"]["medium"],
                        "width": photo["width"],
                        "height": photo["height"],
                        "alt": photo.get("alt", ""),
                    },
                    "like_count": random.randint(12, 980),
                    "is_liked": False,
                    "pexels_url": photo["url"],
                    "created_at": photo.get("created_at", None),
                })

        # Fetch popular videos (fewer, mixed in)
        video_res = http_requests.get(
            f"https://api.pexels.com/videos/popular?page={page}&per_page=4",
            headers=headers,
            timeout=8,
        )

        if video_res.status_code == 200:
            videos = video_res.json().get("videos", [])
            for video in videos:
                author = random.choice(FAKE_AUTHORS)
                # Pick medium quality video file
                video_files = video.get("video_files", [])
                video_url = ""
                for vf in video_files:
                    if vf.get("quality") == "sd" or vf.get("width", 0) <= 1280:
                        video_url = vf["link"]
                        break
                if not video_url and video_files:
                    video_url = video_files[0]["link"]

                # Pick a thumbnail
                video_pics = video.get("video_pictures", [])
                thumbnail = video_pics[0]["picture"] if video_pics else ""

                feed_items.append({
                    "id": f"video_{video['id']}",
                    "type": "video",
                    "author": {
                        "id": video.get("user", {}).get("id", 0),
                        "name": video.get("user", {}).get("name", author["name"]),
                        "email": author["email"],
                        "profile_pic": video.get("user", {}).get("url", None),
                    },
                    "content": random.choice(VIDEO_CAPTIONS),
                    "media": {
                        "type": "video",
                        "url": video_url,
                        "thumbnail": thumbnail,
                        "duration": video.get("duration", 0),
                        "width": video.get("width", 0),
                        "height": video.get("height", 0),
                    },
                    "like_count": random.randint(50, 2000),
                    "is_liked": False,
                    "pexels_url": video.get("url", ""),
                    "created_at": None,
                })

        # Shuffle to mix photos and videos
        random.shuffle(feed_items)

        return Response({
            "page": page,
            "per_page": per_page,
            "total_results": len(feed_items),
            "has_next": len(feed_items) >= per_page,
            "results": feed_items,
        })

    except Exception as e:
        return Response(
            {"error": f"Failed to fetch explore feed: {str(e)}"},
            status=500,
        )
