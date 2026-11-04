from concurrent.futures import ThreadPoolExecutor
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models.job_application import JobApplication


def _unique_key(prefix: str) -> str:
    return f"test_{prefix}_{uuid.uuid4().hex[:10]}"


def _cleanup_key(key: str) -> None:
    with SessionLocal() as db:
        obj = db.scalar(select(JobApplication).where(JobApplication.application_key == key))
        if obj is not None:
            db.delete(obj)
            db.commit()


def test_crud_and_activity_history():
    key = _unique_key("crud")
    try:
        with TestClient(app) as client:
            # 1. Create application (PENDING)
            create_res = client.post(
                "/applications/",
                json={
                    "company": "TestCorp GmbH",
                    "position": "Backend Engineer",
                    "summary": "Initial application submitted via portal.",
                    "status": "PENDING",
                    "email_category": "APPLICATION_RECEIVED",
                    "confidence": 0.96,
                    "application_key": key,
                },
            )
            assert create_res.status_code == 201, create_res.text
            created = create_res.json()
            app_id = created["id"]
            assert created["status"] == "PENDING"
            assert len(created["activities"]) == 1
            assert created["activities"][0]["event_type"] == "CREATED"

            # 2. Update status to INTERVIEW with date and time
            patch_res = client.patch(
                f"/applications/{app_id}",
                json={
                    "status": "INTERVIEW",
                    "interview_date": "12.11.2026",  # also verifies date string normalization
                    "interview_time": "14:30",
                },
            )
            assert patch_res.status_code == 200, patch_res.text
            updated = patch_res.json()
            assert updated["status"] == "INTERVIEW"
            assert updated["interview_date"] == "2026-11-12"
            assert updated["interview_time"].startswith("14:30")

            # 3. Update interview date to a new date
            patch_res_2 = client.patch(
                f"/applications/{app_id}",
                json={"interview_date": "2026-11-18"},
            )
            assert patch_res_2.status_code == 200

            # 4. Inspect GET /applications/{id} details & activity history
            detail_res = client.get(f"/applications/{app_id}")
            assert detail_res.status_code == 200
            detail = detail_res.json()
            event_types = [ev["event_type"] for ev in detail["activities"]]
            assert "CREATED" in event_types
            assert "STATUS_CHANGED" in event_types
            assert event_types.count("INTERVIEW_DATE_UPDATED") == 2
            assert "INTERVIEW_TIME_UPDATED" in event_types

            # 5. Delete application
            del_res = client.delete(f"/applications/{app_id}")
            assert del_res.status_code == 204
            assert client.get(f"/applications/{app_id}").status_code == 404
    finally:
        _cleanup_key(key)


def test_sync_chronology_and_status_progression():
    key = _unique_key("sync_chrono")
    try:
        with TestClient(app) as client:
            # Step 1: Sync initial APPLICATION_RECEIVED email
            r1 = client.post(
                "/applications/sync",
                json={
                    "company": "ChronoTech AG",
                    "position": "AI Engineer",
                    "summary": "We received your application.",
                    "status": "PENDING",
                    "email_category": "APPLICATION_RECEIVED",
                    "confidence": 0.95,
                    "application_key": key,
                    "last_email_at": "2026-11-01T09:00:00Z",
                },
            )
            assert r1.status_code == 200, r1.text
            assert r1.json()["status"] == "PENDING"

            # Step 2: Sync newer INTERVIEW_INVITATION email (also test status auto-derivation from email_category)
            r2 = client.post(
                "/applications/sync",
                json={
                    "company": "ChronoTech AG",
                    "position": "AI Engineer",
                    "summary": "Invitation to technical interview.",
                    "status": "PENDING",  # even if n8n defaults status to PENDING, email_category upgrades it
                    "email_category": "INTERVIEW_INVITATION",
                    "interview_date": "2026-11-22",
                    "interview_time": "2:15 PM",  # 12h format normalized to 14:15:00
                    "confidence": 0.99,
                    "application_key": key,
                    "last_email_at": "2026-11-02T15:30:00Z",
                },
            )
            assert r2.status_code == 200, r2.text
            body2 = r2.json()
            assert body2["status"] == "INTERVIEW"
            assert body2["interview_date"] == "2026-11-22"
            assert body2["interview_time"].startswith("14:15")

            # Step 3: Out-of-order older PENDING email arrives late — must NOT overwrite INTERVIEW
            r3 = client.post(
                "/applications/sync",
                json={
                    "company": "ChronoTech AG",
                    "position": "AI Engineer",
                    "summary": "Older confirmation email.",
                    "status": "PENDING",
                    "email_category": "APPLICATION_RECEIVED",
                    "confidence": 0.90,
                    "application_key": key,
                    "last_email_at": "2026-10-31T08:00:00Z",
                },
            )
            assert r3.status_code == 200
            body3 = r3.json()
            assert body3["status"] == "INTERVIEW"
            assert body3["interview_date"] == "2026-11-22"
            assert body3["interview_time"].startswith("14:15")

            # Verify chronological history preserved all valid transitions
            activities = body3["activities"]
            assert len(activities) >= 3
            assert activities[0]["event_type"] == "CREATED"
            assert any(a["event_type"] == "STATUS_CHANGED" and a["new_value"] == "INTERVIEW" for a in activities)
    finally:
        _cleanup_key(key)


def test_concurrent_sync_requests_do_not_fail_or_duplicate():
    key = _unique_key("concurrent")
    payload_1 = {
        "company": "Parallel Systems GmbH",
        "position": "Cloud Architect",
        "summary": "Application received confirmation.",
        "status": "PENDING",
        "email_category": "APPLICATION_RECEIVED",
        "confidence": 0.92,
        "application_key": key,
        "last_email_at": "2026-11-03T10:00:00Z",
    }
    payload_2 = {
        "company": "Parallel Systems GmbH",
        "position": "Cloud Architect",
        "summary": "Interview invitation for Cloud Architect.",
        "status": "INTERVIEW",
        "email_category": "INTERVIEW_INVITATION",
        "interview_date": "2026-11-25",
        "interview_time": "11:00",
        "confidence": 0.98,
        "application_key": key,
        "last_email_at": "2026-11-03T10:05:00Z",
    }

    def _call_sync(payload: dict):
        with TestClient(app) as client:
            return client.post("/applications/sync", json=payload)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(_call_sync, payload_1), pool.submit(_call_sync, payload_2)]
            responses = [f.result() for f in futures]

        # Neither request may fail with 409 Conflict
        statuses = [r.status_code for r in responses]
        assert statuses == [200, 200], [r.text for r in responses]

        # Both must refer to the exact same application ID (no duplicates)
        ids = {r.json()["id"] for r in responses}
        assert len(ids) == 1

        # Final state must reflect the newer INTERVIEW email
        with TestClient(app) as client:
            final = client.get(f"/applications/{next(iter(ids))}").json()
            assert final["status"] == "INTERVIEW"
            assert final["interview_date"] == "2026-11-25"
            assert final["interview_time"].startswith("11:00")
    finally:
        _cleanup_key(key)

