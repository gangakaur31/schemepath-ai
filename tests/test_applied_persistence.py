"""
test_applied_persistence.py — Unit tests for the 'Mark as Applied' persistence and sync feature.
"""

import os
import sys
import unittest
import tempfile
import shutil

# Add frontend to sys.path so we can import storage
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if FRONTEND_DIR not in sys.path:
    sys.path.insert(0, FRONTEND_DIR)

from storage import (
    get_scheme_id,
    get_user_applications,
    is_scheme_applied,
    mark_as_applied,
    unmark_applied,
    toggle_applied,
)


class TestAppliedPersistence(unittest.TestCase):
    def setUp(self):
        # Create a temporary test directory and file for isolated test persistence
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test_applications.json")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_scheme_id_stability(self):
        """Ensure scheme_id is stable and deterministic."""
        scheme1 = {"scheme_id": "nsp-postmatric", "name": "Post Matric Scholarship"}
        self.assertEqual(get_scheme_id(scheme1), "nsp-postmatric")

        # Fallback to name slug if scheme_id is missing or generic
        scheme2 = {"name": "Prime Minister Special Fellowship for OBC"}
        slug = get_scheme_id(scheme2)
        self.assertEqual(slug, "prime-minister-special-fellowship-for-obc")

        # Consistency across multiple calls
        self.assertEqual(get_scheme_id(scheme2), slug)

    def test_mark_and_retrieve_application(self):
        """Ensure an application is marked and retrievable."""
        user_id = "user_alpha"
        scheme = {
            "scheme_id": "nsp-postmatric",
            "name": "Post Matric SC Scholarship",
            "category": "scholarship",
            "benefit_amount": "₹30,000",
            "portal_url": "https://scholarships.gov.in",
            "description": "Financial aid for SC students",
        }

        self.assertFalse(is_scheme_applied(user_id, "nsp-postmatric", filepath=self.test_file))

        entry = mark_as_applied(user_id, scheme, filepath=self.test_file)
        self.assertEqual(entry["scheme_id"], "nsp-postmatric")
        self.assertEqual(entry["name"], "Post Matric SC Scholarship")
        self.assertIn("marked_at", entry)

        self.assertTrue(is_scheme_applied(user_id, "nsp-postmatric", filepath=self.test_file))
        apps = get_user_applications(user_id, filepath=self.test_file)
        self.assertEqual(len(apps), 1)
        self.assertIn("nsp-postmatric", apps)

    def test_unmark_application(self):
        """Ensure unmarking removes the application."""
        user_id = "user_alpha"
        scheme = {
            "scheme_id": "vidya-lakshmi-loan",
            "name": "Vidya Lakshmi Education Loan",
            "category": "education_loan",
        }

        mark_as_applied(user_id, scheme, filepath=self.test_file)
        self.assertTrue(is_scheme_applied(user_id, "vidya-lakshmi-loan", filepath=self.test_file))

        # Unmark
        removed = unmark_applied(user_id, "vidya-lakshmi-loan", filepath=self.test_file)
        self.assertTrue(removed)
        self.assertFalse(is_scheme_applied(user_id, "vidya-lakshmi-loan", filepath=self.test_file))

        apps = get_user_applications(user_id, filepath=self.test_file)
        self.assertEqual(len(apps), 0)

    def test_duplicate_prevention(self):
        """Ensure marking the same scheme multiple times creates exactly 1 entry."""
        user_id = "user_alpha"
        scheme = {
            "scheme_id": "pm-internship",
            "name": "PM Internship Scheme",
            "category": "internship",
        }

        mark_as_applied(user_id, scheme, filepath=self.test_file)
        mark_as_applied(user_id, scheme, filepath=self.test_file)
        mark_as_applied(user_id, scheme, filepath=self.test_file)

        apps = get_user_applications(user_id, filepath=self.test_file)
        self.assertEqual(len(apps), 1, "Duplicate entries must be prevented")

    def test_toggle_applied(self):
        """Ensure toggle_applied alternates between applied and unapplied."""
        user_id = "user_alpha"
        scheme = {
            "scheme_id": "dst-inspire",
            "name": "DST INSPIRE Fellowship",
            "category": "research_fellowship",
        }

        # First toggle: should mark as applied (return True)
        state1 = toggle_applied(user_id, scheme, filepath=self.test_file)
        self.assertTrue(state1)
        self.assertTrue(is_scheme_applied(user_id, "dst-inspire", filepath=self.test_file))

        # Second toggle: should unmark (return False)
        state2 = toggle_applied(user_id, scheme, filepath=self.test_file)
        self.assertFalse(state2)
        self.assertFalse(is_scheme_applied(user_id, "dst-inspire", filepath=self.test_file))

    def test_multi_user_isolation(self):
        """Ensure user A's applied schemes are strictly isolated from user B."""
        user_a = "user_1001"
        user_b = "user_2002"

        scheme_a = {"scheme_id": "scheme_a", "name": "Scheme A"}
        scheme_b = {"scheme_id": "scheme_b", "name": "Scheme B"}

        mark_as_applied(user_a, scheme_a, filepath=self.test_file)
        mark_as_applied(user_b, scheme_b, filepath=self.test_file)

        apps_a = get_user_applications(user_a, filepath=self.test_file)
        apps_b = get_user_applications(user_b, filepath=self.test_file)

        self.assertEqual(len(apps_a), 1)
        self.assertEqual(len(apps_b), 1)
        self.assertIn("scheme_a", apps_a)
        self.assertNotIn("scheme_b", apps_a)
        self.assertIn("scheme_b", apps_b)
        self.assertNotIn("scheme_a", apps_b)

    def test_disk_persistence_across_reloads(self):
        """Ensure that data persists on disk and is correctly reloaded."""
        user_id = "persistent_user"
        scheme = {
            "scheme_id": "persistent_scheme",
            "name": "State Post Matric Scholarship",
            "category": "scholarship",
            "benefit_amount": "₹15,000",
        }

        mark_as_applied(user_id, scheme, filepath=self.test_file)

        # Verify raw file exists on disk
        self.assertTrue(os.path.exists(self.test_file))

        # Simulate fresh process reload by re-reading from disk
        reloaded_apps = get_user_applications(user_id, filepath=self.test_file)
        self.assertIn("persistent_scheme", reloaded_apps)
        self.assertEqual(reloaded_apps["persistent_scheme"]["name"], "State Post Matric Scholarship")
        self.assertEqual(reloaded_apps["persistent_scheme"]["benefit_amount"], "₹15,000")


if __name__ == "__main__":
    unittest.main()
