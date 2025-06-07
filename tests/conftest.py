import os
import django


def pytest_configure():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coupon_core.settings.test')
    django.setup()
