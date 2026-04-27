from rest_framework import serializers
from .models import CustomUser

class UserSerializer(serializers.ModelSerializer):

    avatar_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'avatar_url',
            'cover_url'
        ]

    def get_avatar_url(self, obj):
        if obj.avatar:
            return f"{obj.avatar.url}?v={obj.avatar_version}"
        return None

    def get_cover_url(self, obj):
        if obj.cover:
            return f"{obj.cover.url}?v={obj.cover_version}"
        return None