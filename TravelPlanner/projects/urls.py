from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"projects", views.ProjectViewSet, basename="projects")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "projects/<int:project_id>/places/",
        views.PlaceListCreateView.as_view(),
        name="place-list",
    ),
    path(
        "projects/<int:project_id>/places/<int:pk>/",
        views.PlaceDetailView.as_view(),
        name="place-detail",
    ),
]