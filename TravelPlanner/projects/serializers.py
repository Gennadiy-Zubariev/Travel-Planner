from django.conf import settings
from rest_framework import serializers
from .models import Place, Project


class PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = ["id", "project", "external_id", "title", "artist",
                  "notes", "is_visited", "visited_at", "created_at"]
        read_only_fields = ["title", "artist", "visited_at", "created_at", "project"]


class PlaceInputSerializer(serializers.Serializer):
    """Для створення місця всередині проекту."""
    external_id = serializers.CharField(max_length=64)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class PlaceUpdateSerializer(serializers.Serializer):
    """Для PATCH місця."""
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_visited = serializers.BooleanField(required=False)


class ProjectSerializer(serializers.ModelSerializer):
    places = PlaceSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ["id", "name", "description", "start_date", "status",
                  "places", "created_at"]
        read_only_fields = ["status", "places", "created_at"]


class ProjectCreateSerializer(serializers.ModelSerializer):
    places = PlaceInputSerializer(many=True, required=False, default=list)

    class Meta:
        model = Project
        fields = ["name", "description", "start_date", "places"]

    def validate_places(self, value):
        if len(value) > settings.MAX_PLACES_PER_PROJECT:
            raise serializers.ValidationError(
                f"Maximum {settings.MAX_PLACES_PER_PROJECT} places allowed"
            )
        ids = [p["external_id"] for p in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Duplicate external_id")
        return value