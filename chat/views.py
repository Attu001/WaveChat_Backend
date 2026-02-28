from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from authorization.models import User
from authorization.utils import generate_token_verification
from django.shortcuts import get_object_or_404
from rest_framework import status
from django.conf import settings
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import ChatRequest,Chat
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
    receiver = get_object_or_404(User, id=user_id)

    if receiver == request.user:
        return Response({"error": "Cannot send request to yourself"}, status=400)

    chat_request, created = ChatRequest.objects.get_or_create(
        sender=request.user,
        receiver=receiver,
    )


    if not created:
        return Response({"error": "Request already exists"}, status=400)
    
    create_and_send_notification(
    sender=request.user,
    receiver=receiver,
    message=f"{request.user.name} has sent you a chat request."
    )
    
    return Response({"message": "Chat request sent"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pending_requests(request):
    requests = ChatRequest.objects.filter(
        receiver=request.user,
        status=ChatRequest.PENDING
    )
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
    current_user = request.user

    # all other users
    users = User.objects.exclude(id=current_user.id).values("id", "name", "email", "profile_pic")

   # accepted chats (friends)
    accepted_user_ids = set()

    private_chats = Chat.objects.filter(
                is_group=False,
                participants=current_user
            ).prefetch_related("participants")

    for chat in private_chats:
        other_user = chat.participants.exclude(id=current_user.id).first()
        if other_user:
                accepted_user_ids.add(other_user.id)


    # sent pending requests
    sent_requests = set(
        ChatRequest.objects.filter(
            sender=current_user,
            status=ChatRequest.PENDING
        ).values_list("receiver_id", flat=True)
    )

    # received pending requests
    received_requests = {
        r.sender_id: r.id
        for r in ChatRequest.objects.filter(
            receiver=current_user,
            status=ChatRequest.PENDING
        )
    }

    data = []

    for user in users:
        uid = user["id"]

        if uid in accepted_user_ids:
            status_value = "ACCEPTED"
            request_id = None

        elif uid in sent_requests:
            status_value = "PENDING_SENT"
            request_id = None

        elif uid in received_requests:
            status_value = "PENDING_RECEIVED"
            request_id = received_requests[uid]

        else:
            status_value = "NONE"
            request_id = None

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

