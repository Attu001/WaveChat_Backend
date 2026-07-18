from django.urls import path
from . import views

urlpatterns = [
    # ===== Chat Requests =====
    path("requests/send/<int:user_id>/", views.send_chat_request, name="send-chat-request"),
    path("requests/pending/", views.pending_requests, name="pending-chat-requests"),
    path("requests/reject/<int:request_id>/", views.reject_request, name="reject-chat-request"),
    path("users-with-status/", views.users_with_status, name="users-with-status"),
    path("requests/accept/<int:request_id>/", views.accept_request, name="accept-chat-request"),
    path("notifications/", views.get_user_notifications, name="user-notifications"),
    path("notifications/unread-count/", views.unread_notification_count, name="unread-notification-count"),
    path("notifications/mark-read/<int:notification_id>/", views.mark_notification_read, name="mark-notification-read"),
    path("notifications/mark-all-read/", views.mark_all_notifications_read, name="mark-all-notifications-read"),
    path("history/<int:other_user_id>/", views.chat_history, name="chat-history"),

    # ===== Posts =====
    path("posts/", views.list_posts, name="list-posts"),
    path("posts/create/", views.create_post, name="create-post"),
    path("posts/<int:post_id>/like/", views.toggle_like, name="toggle-like"),
    path("posts/<int:post_id>/delete/", views.delete_post, name="delete-post"),

    # ===== Explore =====
    path("explore/", views.explore_feed, name="explore-feed"),
]
