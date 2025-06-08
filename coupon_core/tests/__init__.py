"""Test helpers for the :mod:`coupon_core.tests` package."""

import os

# Ensure tests run with the lightweight SQLite settings.  Individual test
# modules handle their own skipping when dependencies like Django or Celery are
# unavailable, so we only need to set the settings module here.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coupon_core.settings.test")

# The previous version of this module imported all test modules on import which
# caused import errors when optional dependencies were missing.  Tests are now
# discovered normally by pytest without eager imports.

