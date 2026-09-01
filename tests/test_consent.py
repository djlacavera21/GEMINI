from pathlib import Path

import pytest

from gemini_cloner.consent import (
    ConsentError,
    approval_url,
    approve_job,
    make_job,
    require_approved,
    verify_token,
)


def test_job_roundtrip(tmp_path: Path):
    job = make_job(
        tmp_path,
        phone="+15555550100",
        platform="android",
        serial="ABC123",
        scope=["media", "documents"],
        operator="test",
        ttl_minutes=10,
        public_base="http://127.0.0.1:8787",
    )
    assert job["status"] == "pending"
    url = approval_url(job)
    assert job["job_id"] in url
    loaded = verify_token(tmp_path, job["job_id"], job["token"])
    assert loaded["serial"] == "ABC123"


def test_bad_token_rejected(tmp_path: Path):
    job = make_job(
        tmp_path,
        phone="+15555550100",
        platform="android",
        serial="ABC123",
        scope=["media"],
        operator="test",
    )
    with pytest.raises(ConsentError):
        verify_token(tmp_path, job["job_id"], "deadbeef")


def test_approve_binds_challenge(tmp_path: Path):
    job = make_job(
        tmp_path,
        phone="+15555550100",
        platform="android",
        serial="ABC123",
        scope=["packages"],
        operator="test",
    )
    with pytest.raises(ConsentError):
        approve_job(
            tmp_path,
            job["job_id"],
            job["token"],
            method="passkey",
            client_data={"challenge": "wrong"},
        )
    approved = approve_job(
        tmp_path,
        job["job_id"],
        job["token"],
        method="passkey",
        client_data={"challenge": job["challenge"]},
        credential_id="cred-1",
    )
    assert approved["status"] == "approved"
    assert require_approved(tmp_path, job["job_id"])["approvals"][0]["credential_id"] == "cred-1"


def test_unknown_scope(tmp_path: Path):
    with pytest.raises(ConsentError):
        make_job(
            tmp_path,
            phone="+1",
            platform="android",
            serial="x",
            scope=["root-bypass"],
            operator="test",
        )
