"""Database models for the Travel Planner app."""

from django.db import models
from django.utils import timezone


class Project(models.Model):
    """A travel project — a collection of places a traveller wants to visit."""

    class Status(models.TextChoices):
        PLANNING = "planning", "Planning"
        COMPLETED = "completed", "Completed"

    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def has_visited_places(self) -> bool:
        return self.places.filter(is_visited=True).exists()

    def refresh_status(self) -> "Project":
        """Recompute status based on whether all places are visited.

        Called whenever a place's `is_visited` flag flips or a new place is added,
        so the project status is always consistent with its places.
        """
        places = list(self.places.all())
        if places and all(p.is_visited for p in places):
            new_status = self.Status.COMPLETED
        else:
            new_status = self.Status.PLANNING
        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=["status", "updated_at"])
        return self


class Place(models.Model):
    """A place (artwork) attached to a project.

    Identified by `external_id` from the Art Institute of Chicago API.
    The `(project, external_id)` pair is unique to prevent duplicates.
    """

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="places")
    external_id = models.CharField(max_length=64, db_index=True)

    # Display metadata cached from the third-party API.
    title = models.CharField(max_length=500, blank=True, null=True)
    artist = models.CharField(max_length=500, blank=True, null=True)
    image_id = models.CharField(max_length=255, blank=True, null=True)

    notes = models.TextField(blank=True, null=True)
    is_visited = models.BooleanField(default=False)
    visited_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "external_id"], name="uq_project_external_place"
            ),
        ]

    def __str__(self):
        return f"{self.title or self.external_id} (project={self.project_id})"

    def mark_visited(self, visited: bool) -> None:
        """Update `is_visited` and bookkeep `visited_at` accordingly."""
        if visited and not self.is_visited:
            self.visited_at = timezone.now()
        elif not visited and self.is_visited:
            self.visited_at = None
        self.is_visited = visited