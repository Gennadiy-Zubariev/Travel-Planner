from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from projects.services.artic import PlaceNotFoundError


def _fake_artwork(external_id: str) -> dict:
    """Return a fake successful response from the Art Institute API."""
    return {
        "id": int(external_id),
        "title": f"Artwork {external_id}",
        "artist_title": "Test Artist",
        "image_id": f"img-{external_id}",
    }


class HealthTests(TestCase):
    def test_health(self):
        self.assertEqual(self.client.get("/health/").status_code, 200)


# We patch validate_and_fetch_place in the `views` module where it's used.
MOCK_PATH = "projects.views.validate_and_fetch_place"


class ProjectLifecycleTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_full_lifecycle(self):
        with patch(MOCK_PATH, side_effect=_fake_artwork):
            # 1) Create project with two places in one shot
            resp = self.client.post(
                "/projects/",
                {
                    "name": "Italy 2026",
                    "description": "Summer trip",
                    "start_date": "2026-07-01",
                    "places": [
                        {"external_id": "111", "notes": "Famous painting"},
                        {"external_id": "222"},
                    ],
                },
                format="json",
            )
            self.assertEqual(resp.status_code, 201, resp.content)
            project = resp.json()
            pid = project["id"]
            self.assertEqual(project["status"], "planning")
            self.assertEqual(len(project["places"]), 2)

            # 2) List projects
            list_resp = self.client.get("/projects/?page=1&page_size=10")
            self.assertEqual(list_resp.status_code, 200)
            self.assertGreaterEqual(list_resp.json()["total"], 1)

            # 3) Add a third place via the nested endpoint
            resp = self.client.post(
                f"/projects/{pid}/places/", {"external_id": "333"}, format="json"
            )
            self.assertEqual(resp.status_code, 201, resp.content)
            place3_id = resp.json()["id"]

            # 4) Duplicate add → 409
            dup = self.client.post(
                f"/projects/{pid}/places/", {"external_id": "333"}, format="json"
            )
            self.assertEqual(dup.status_code, 409)

            # 5) Update notes
            upd = self.client.patch(
                f"/projects/{pid}/places/{place3_id}/",
                {"notes": "Audio guide recommended"},
                format="json",
            )
            self.assertEqual(upd.status_code, 200)
            self.assertEqual(upd.json()["notes"], "Audio guide recommended")

            # 6) Cannot delete a project once a place is visited
            self.client.patch(
                f"/projects/{pid}/places/{place3_id}/",
                {"is_visited": True},
                format="json",
            )
            deny = self.client.delete(f"/projects/{pid}/")
            self.assertEqual(deny.status_code, 409)

            # 7) Mark every place as visited → project becomes completed
            for place in project["places"]:
                self.client.patch(
                    f"/projects/{pid}/places/{place['id']}/",
                    {"is_visited": True},
                    format="json",
                )
            full = self.client.get(f"/projects/{pid}/").json()
            self.assertEqual(full["status"], "completed")
            self.assertTrue(all(p["is_visited"] for p in full["places"]))

            # 8) Un-mark one place → status flips back to planning
            self.client.patch(
                f"/projects/{pid}/places/{full['places'][0]['id']}/",
                {"is_visited": False},
                format="json",
            )
            again = self.client.get(f"/projects/{pid}/").json()
            self.assertEqual(again["status"], "planning")


class ValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_max_places_limit(self):
        with patch(MOCK_PATH, side_effect=_fake_artwork):
            payload = {
                "name": "Too many",
                "places": [{"external_id": str(i)} for i in range(1, 12)],
            }
            resp = self.client.post("/projects/", payload, format="json")
            self.assertEqual(resp.status_code, 400)  # DRF returns 400 for validation errors

    def test_duplicate_external_ids_in_payload(self):
        with patch(MOCK_PATH, side_effect=_fake_artwork):
            resp = self.client.post(
                "/projects/",
                {
                    "name": "Dupes",
                    "places": [{"external_id": "5"}, {"external_id": "5"}],
                },
                format="json",
            )
            self.assertEqual(resp.status_code, 400)

    def test_external_place_not_found(self):
        def _missing(_eid):
            raise PlaceNotFoundError(_eid)

        with patch(MOCK_PATH, side_effect=_missing):
            resp = self.client.post(
                "/projects/",
                {"name": "Ghost", "places": [{"external_id": "9999999"}]},
                format="json",
            )
            self.assertEqual(resp.status_code, 404)

    def test_get_nonexistent_project(self):
        self.assertEqual(self.client.get("/projects/999999/").status_code, 404)

    def test_invalid_payload_empty_name(self):
        resp = self.client.post("/projects/", {"name": ""}, format="json")
        self.assertEqual(resp.status_code, 400)
