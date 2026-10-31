"""
storage.py — Lightweight, user-isolated persistence for applied schemes in AVSAR.

Stores applications locally in JSON format (backend/data/user_applications.json)
so selections survive browser refreshes and application restarts without adding
a heavy database.
"""

import json
import os
import re
import tempfile
from datetime import datetime
from typing import Dict, Any, List

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "data"))
DATA_FILE = os.path.join(DATA_DIR, "user_applications.json")


def get_scheme_id(scheme: Dict[str, Any]) -> str:
    """
    Return a stable, deterministic identifier for a scheme.
    Uses the official scheme_id if present; otherwise derives a stable slug from the name.
    """
    sid = str(scheme.get("scheme_id") or "").strip()
    # Only fall back to name slug if scheme_id is missing or an ephemeral index like "scheme_0"
    if sid and not re.match(r"^scheme_\d+$", sid):
        return sid

    name = str(scheme.get("name") or "").strip().lower()
    if name:
        slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
        if slug:
            return slug

    return sid or "unknown-scheme"


def _load_all_records(filepath: str = DATA_FILE) -> Dict[str, Dict[str, Any]]:
    """Read all user application records safely from disk."""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except Exception:
        return {}


def _save_all_records(records: Dict[str, Dict[str, Any]], filepath: str = DATA_FILE) -> None:
    """Write all user application records to disk atomically."""
    dir_name = os.path.dirname(filepath)
    os.makedirs(dir_name, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
        json.dump(records, tf, indent=2, ensure_ascii=False)
        temp_name = tf.name

    os.replace(temp_name, filepath)


def get_user_applications(user_id: str, filepath: str = DATA_FILE) -> Dict[str, Dict[str, Any]]:
    """Get all applications marked as applied by a specific user."""
    uid = str(user_id or "default_user").strip()
    all_records = _load_all_records(filepath)
    return dict(all_records.get(uid, {}))


def is_scheme_applied(user_id: str, scheme_id: str, filepath: str = DATA_FILE) -> bool:
    """Check whether a specific scheme is marked as applied by the user."""
    apps = get_user_applications(user_id, filepath)
    return str(scheme_id) in apps


def mark_as_applied(user_id: str, scheme: Dict[str, Any], filepath: str = DATA_FILE) -> Dict[str, Any]:
    """
    Mark a scheme as applied for a user.
    Prevents duplicate entries by keying on the stable scheme_id.
    """
    uid = str(user_id or "default_user").strip()
    sid = get_scheme_id(scheme)

    all_records = _load_all_records(filepath)
    user_apps = all_records.setdefault(uid, {})

    entry = {
        "scheme_id": sid,
        "name": scheme.get("name", "Government Scheme"),
        "category": scheme.get("category", "scholarship"),
        "benefit_amount": scheme.get("benefit_amount", ""),
        "description": scheme.get("description", ""),
        "portal_url": scheme.get("portal_url", ""),
        "documents_required": scheme.get("documents_required", []),
        "marked_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }

    # Dict assignment guarantees duplicate prevention
    user_apps[sid] = entry
    _save_all_records(all_records, filepath)
    return entry


def unmark_applied(user_id: str, scheme_id: str, filepath: str = DATA_FILE) -> bool:
    """
    Remove an applied scheme entry for a user.
    Returns True if removed, False if not found.
    """
    uid = str(user_id or "default_user").strip()
    sid = str(scheme_id).strip()

    all_records = _load_all_records(filepath)
    user_apps = all_records.get(uid, {})

    if sid in user_apps:
        del user_apps[sid]
        _save_all_records(all_records, filepath)
        return True
    return False


def toggle_applied(user_id: str, scheme: Dict[str, Any], filepath: str = DATA_FILE) -> bool:
    """
    Toggle application status for a scheme.
    Returns True if scheme is now marked as applied, False if unmarked.
    """
    sid = get_scheme_id(scheme)
    if is_scheme_applied(user_id, sid, filepath):
        unmark_applied(user_id, sid, filepath)
        return False
    else:
        mark_as_applied(user_id, scheme, filepath)
        return True
