from coupon_core.celery import celery_app  as app
from urllib.parse import urlparse
from geodiscounts.v1.utils.fetch_discounts import import_discounts_from_spaces
from django.conf import settings
@app.task
def import_discounts_task(file_url=None):
    """
    Celery task to trigger import_discounts_from_spaces with a full DO Spaces file URL or prefix.

    If a single file URL is provided, it will import just that JSON file.
    If a prefix is provided, it will import all matching JSONs.
    """
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    prefix = None
    if file_url:
        parsed = urlparse(file_url)
        # Host format: <bucket>.<region>.digitaloceanspaces.com
        bucket_name = parsed.netloc.split('.')[0]
        key = parsed.path.lstrip('/')
        # If URL points to a file, treat key as prefix and import single
        prefix = key
    return import_discounts_from_spaces(bucket_name=bucket_name, prefix=prefix)