import os
import pytest

try:
    import django
except Exception:
    pytest.skip("django not installed", allow_module_level=True)


def pytest_configure():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon_core.settings.test')
    django.setup()
