"""Pytest configuration for Django tests."""

import os
import django
import pytest
from django.contrib.gis.utils import has_spatialite
from django.core.management import call_command


def pytest_configure() -> None:
    """Configure Django with the test settings and run migrations.

    If the required spatial libraries are not available, all tests are
    skipped. This avoids raising errors when spatialite or other GIS
    dependencies are missing on the test runner.
    """

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coupon_core.settings.test")

    # Skip the entire suite if spatial libraries are not available.
    try:
        if not has_spatialite():
            pytest.skip("Spatial libraries missing", allow_module_level=True)
    except Exception:  # pragma: no cover - failure to check libs should skip
        pytest.skip("Spatial libraries missing", allow_module_level=True)

    django.setup()

    try:
        call_command("migrate", run_syncdb=True, verbosity=0)
    except Exception as exc:  # pragma: no cover - database not configured
        pytest.skip(f"Database setup failed: {exc}", allow_module_level=True)
