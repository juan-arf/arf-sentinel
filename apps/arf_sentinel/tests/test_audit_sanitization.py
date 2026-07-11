from apps.arf_sentinel.audit import AuditLogger
import tempfile, os, json

def test_sanitization_removes_secrets():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = AuditLogger(tmpdir)
        record = {
            "timestamp": "2025-01-01T00:00:00Z",
            "incident_id": "test",
            "event_type": "TEST",
            "actor": "USER",
            "action": "test",
            "metadata": {
                "api_key": "secret123",
                "Authorization": "Bearer xyz",
                "refresh_token": "rt-abc",
                "access_token": "at-def"
            }
        }
        sanitized = logger._sanitize(record)
        meta = sanitized["metadata"]
        assert "api_key" not in meta
        assert "Authorization" not in meta
        assert "refresh_token" not in meta
        assert "access_token" not in meta
