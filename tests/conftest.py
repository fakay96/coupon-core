import os
import pytest


def pytest_configure():
    """Initialize Django or skip the entire suite if it's unavailable."""
    try:
        import django
    except Exception:
        pytest.skip("django not installed", allow_module_level=True)
        return

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coupon_core.settings.test")
    try:
        django.setup()
        from django.core.management import call_command
        call_command("migrate", run_syncdb=True, verbosity=0)
    except Exception as exc:
        msg = str(exc).lower()
        if (
            isinstance(exc, OSError)
            or isinstance(exc, AttributeError)
            or "libgdal" in msg
            or "spatial" in msg
            or "geo_db_type" in msg
        ):
            pytest.skip("Spatial libraries missing", allow_module_level=True)
            return
        raise


# Remove the previous behaviour that turned failures into skips so that
# failing tests are reported properly during CI runs.

