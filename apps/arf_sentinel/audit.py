import json
import time
from pathlib import Path
from .models import AuditRecord
from pydantic import BaseModel

class AuditLogger:
    def __init__(self, base_dir: str):
        self.base_path = Path(base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.audit_file = self.base_path / "audit_log.jsonl"

    def log(self, record: AuditRecord):
        sanitized = self._sanitize(record.dict())
        with open(self.audit_file, "a") as f:
            f.write(json.dumps(sanitized) + "\n")

    def save_artifact(self, filename: str, data: dict | list | str | BaseModel):
        path = self.base_path / filename
        with open(path, "w") as f:
            if isinstance(data, BaseModel):
                f.write(data.json(indent=2))
            elif isinstance(data, (dict, list)):
                json.dump(data, f, indent=2, default=str)
            else:
                f.write(data)

    def _sanitize(self, record: dict) -> dict:
        sensitive_keys = {"api_key", "authorization", "token", "refresh_token", "access_token", "bearer"}
        meta = record.get("metadata", {})
        for key in list(meta.keys()):
            if any(s in key.lower() for s in sensitive_keys):
                del meta[key]
        record["metadata"] = meta
        return record

def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
