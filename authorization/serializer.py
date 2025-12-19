from rest_framework import serializers
from .models import User


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id","email","name"]