# Serializers: input validation for Register, Login, KB query, and output formatting
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import KBEntry, QueryLog


# ─── Auth Serializers ─────────────────────────────────────────────────────────

class RegisterSerializer(serializers.Serializer):
    """Validates the payload for POST /api/auth/register/"""
    username     = serializers.CharField(max_length=150)
    password     = serializers.CharField(write_only=True, min_length=8)
    company_name = serializers.CharField(max_length=255)
    email        = serializers.EmailField()

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A company with this username already exists.")
        return value


class LoginSerializer(serializers.Serializer):
    """Validates the payload for POST /api/auth/login/"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


# ─── KB Serializers ───────────────────────────────────────────────────────────

class KBEntrySerializer(serializers.ModelSerializer):
    """Serialises KBEntry objects returned in query results."""

    class Meta:
        model  = KBEntry
        fields = ['id', 'question', 'answer', 'category']


class KBQuerySerializer(serializers.Serializer):
    """Validates the payload for POST /api/kb/query/"""
    search = serializers.CharField(
        max_length=255,
        allow_blank=False,
        error_messages={'blank': 'The search field must not be blank.'},
    )


# ─── Admin Serializers ────────────────────────────────────────────────────────

class TopSearchTermSerializer(serializers.Serializer):
    """One entry in the top_search_terms list."""
    search_term = serializers.CharField()
    count       = serializers.IntegerField()
