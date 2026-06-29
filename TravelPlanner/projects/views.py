import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets, generics
from rest_framework.response import Response

from .models import Place, Project
from .serializers import (
    PlaceInputSerializer,
    PlaceSerializer,
    PlaceUpdateSerializer,
    ProjectCreateSerializer,
    ProjectSerializer,
)


def fetch_artwork(external_id):
    """Йдемо в Art Institute API. Повертаємо dict або None."""
    url = f"{settings.ARTIC_API_BASE_URL}/artworks/{external_id}"
    response = requests.get(url, timeout=settings.ARTIC_API_TIMEOUT)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json().get("data")


class ProjectViewSet(viewsets.ModelViewSet):
    """CRUD для проектів."""
    queryset = Project.objects.all().prefetch_related("places")
    http_method_names = ["get", "post", "patch", "delete"]

    def get_serializer_class(self):
        if self.action == "create":
            return ProjectCreateSerializer
        return ProjectSerializer

    def create(self, request):
        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        places_input = data.pop("places", [])

        # Валідуємо кожне місце в зовнішньому API
        places_to_create = []
        for p in places_input:
            artwork = fetch_artwork(p["external_id"])
            if artwork is None:
                return Response(
                    {"detail": f"Place {p['external_id']} not found in external API"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            places_to_create.append({
                "external_id": str(artwork["id"]),
                "title": artwork.get("title"),
                "artist": artwork.get("artist_title"),
                "notes": p.get("notes"),
            })

        # Створюємо проект і місця
        project = Project.objects.create(**data)
        for pd in places_to_create:
            Place.objects.create(project=project, **pd)

        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        project = self.get_object()
        if project.has_visited_places():
            return Response(
                {"detail": "Cannot delete a project with visited places"},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)


class PlaceListCreateView(generics.ListCreateAPIView):
    """Список і додавання місць до проекту."""
    serializer_class = PlaceSerializer

    def get_queryset(self):
        project_id = self.kwargs["project_id"]
        get_object_or_404(Project, pk=project_id)
        return Place.objects.filter(project_id=project_id)

    def create(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)

        input_serializer = PlaceInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        external_id = input_serializer.validated_data["external_id"]
        notes = input_serializer.validated_data.get("notes")

        # Ліміт 10 місць
        if project.places.count() >= settings.MAX_PLACES_PER_PROJECT:
            return Response(
                {"detail": f"Maximum {settings.MAX_PLACES_PER_PROJECT} places allowed"},
                status=status.HTTP_409_CONFLICT,
            )

        # Дублікати
        if project.places.filter(external_id=external_id).exists():
            return Response(
                {"detail": "Place already exists in this project"},
                status=status.HTTP_409_CONFLICT,
            )

        # Валідація у зовнішньому API
        artwork = fetch_artwork(external_id)
        if artwork is None:
            return Response(
                {"detail": f"Place {external_id} not found in external API"},
                status=status.HTTP_404_NOT_FOUND,
            )

        place = Place.objects.create(
            project=project,
            external_id=str(artwork["id"]),
            title=artwork.get("title"),
            artist=artwork.get("artist_title"),
            notes=notes,
        )
        project.refresh_status()
        return Response(PlaceSerializer(place).data, status=status.HTTP_201_CREATED)


class PlaceDetailView(generics.GenericAPIView):
    """Перегляд і оновлення одного місця."""
    serializer_class = PlaceSerializer
    http_method_names = ["get", "patch"]

    def get_object(self):
        return get_object_or_404(
            Place,
            pk=self.kwargs["pk"],
            project_id=self.kwargs["project_id"],
        )

    def get(self, request, *args, **kwargs):
        return Response(PlaceSerializer(self.get_object()).data)

    def patch(self, request, *args, **kwargs):
        place = self.get_object()
        serializer = PlaceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "is_visited" in data:
            place.mark_visited(data["is_visited"])
        if "notes" in data:
            place.notes = data["notes"]
        place.save()

        if "is_visited" in data:
            place.project.refresh_status()

        return Response(PlaceSerializer(place).data)