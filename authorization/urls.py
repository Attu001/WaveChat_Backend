from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_user, name='login'),
    path('verify/', views.verify_email, name='verify_user'),
    path('all_users/',views.get_all_users,name='all Users'),
    path('profile/',views.get_profile,name='profile'),
    path("auth/profile/<int:user_id>/", get_user_profile),

    
]
