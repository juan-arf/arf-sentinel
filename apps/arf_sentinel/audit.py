"""
Audit logging and JSON artifact persistence.

This module implements a lightweight audit trail for ARF Sentinel.
Every significant event in the governance pipeline is recorded as a
structured JSON Lines entry in `audit_log.jsonl`.  Additionally, all
evidence bundles, proposals, decisions, and execution results are
saved as separate JSON artifacts for offline review.

Security
--------
The logger automatically sanitises sensitive keys (API keys, tokens,
authorisation headers) from metadata before writing to disk.  This
prevents accidental credential leakage in the audit trail.

Output Structure
----------------
Each investigation creates a directory under `runs/`:

    runs/sentinel_{incident_id}_{timestamp}/
        audit_log.jsonl           # JSON Lines audit log
        incident.json             # Incident summary
        evidence_bundle.json      # Full CRAFT evidence
        remediation_proposal.json # Agent proposal
        arf_decision.json         # ARF governance decision
        execution_result.json     # Execution boundary outcome
        sql_queries.txt           # SQL queries (if any)

The log is append‑only and line‑oriented for easy ingestion by log
aggregators or forensic tools.
"""

import json
import time
from pathlib import Path
from .models import AuditRecord
from pydantic import BaseModel


class AuditLogger:
    """
    Manages audit log files and artifact saving with automatic
    secret sanitisation.

    Parameters
    ----------
    base_dir : str
        The directory where all artifacts for this incident will be stored.
        It is created if it does not exist.
    """

    def __init__(self, base_dir: str):
        self.base_path = Path(base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.audit_file = self.base_path / "audit_log.jsonl"

    def log(self, record: AuditRecord):
        """
        Append a sanitised JSON line to the audit log.

        The record is first passed through `_sanitize` to strip any
        sensitive metadata, then serialised and written as a single
        line.

        Parameters
        ----------
        record : AuditRecord
            A structured audit entry containing timestamp, incident ID,
            event type, actor, action, and optional decision/metadata.
        """
        sanitized = self._sanitize(record.model_dump())
        with open(self.audit_file, "a") as f:
            f.write(json.dumps(sanitized) + "\n")

    def save_artifact(self, filename: str, data: dict | list | str | BaseModel):
        """
        Save a JSON, list, string, or Pydantic model artifact to a file.

        Pydantic models are serialised using their `.json()` method,
        dictionaries and lists are pretty‑printed with `json.dump`,
        and strings are written verbatim.  Non‑serialisable objects
        in dicts/lists fall back to `str()`.

        Parameters
        ----------
        filename : str
            The name of the artifact file (e.g., 'evidence_bundle.json').
        data : dict | list | str | BaseModel
            The data to persist.
        """
        path = self.base_path / filename
        with open(path, "w") as f:
            if isinstance(data, BaseModel):
                f.write(data.model_dump_json(indent=2))
            elif isinstance(data, (dict, list)):
                json.dump(data, f, indent=2, default=str)
            else:
                f.write(data)

    def _sanitize(self, record: dict) -> dict:
        """
        Remove sensitive keys from a record's metadata.

        Keys matching any of the following patterns (case‑insensitive)
        are deleted from the `metadata` sub‑dictionary:

            - api_key
            - authorization
            - token
            - refresh_token
            - access_token
            - bearer

        This prevents accidental logging of credentials.  The original
        record is not modified; a sanitised copy is returned.

        Parameters
        ----------
        record : dict
            A dictionary representing an audit record (typically from
            `AuditRecord.model_dump()`).

        Returns
        -------
        dict
            The sanitised record dictionary.
        """
        sensitive_keys = {
            "api_key", "authorization", "token", "refresh_token",
            "access_token", "bearer",
        }
        meta = record.get("metadata", {})
        cleaned_meta = {
            k: v
            for k, v in meta.items()
            if not any(sens in k.lower() for sens in sensitive_keys)
        }
        record["metadata"] = cleaned_meta
        return record


def timestamp() -> str:
    """
    Return the current UTC timestamp as an ISO‑8601‑like string.

    The format is `YYYY-MM-DDTHH:MM:SSZ`, which is compatible with
    both human readability and log‑parsing tools.

    Returns
    -------
    str
        Current UTC time formatted as a string.
    """
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
