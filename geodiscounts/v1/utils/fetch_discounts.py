
"""
Fetch JSON batches from DigitalOcean Spaces and import discounts into database.
"""
import json
import logging
from pathlib import Path

import boto3
from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta

from geodiscounts.models import Discount, Retailer, Category
from .storage import StorageService

logger = logging.getLogger(__name__)

def import_discounts_from_spaces(bucket_name=None, prefix=None):
    """
    Fetches JSON files from a DigitalOcean Space using StorageService and imports/updates Discount records.
    """
    bucket = bucket_name or settings.AWS_STORAGE_BUCKET_NAME

    session = boto3.session.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    client = session.client(
        's3', region_name='fra1', endpoint_url=settings.AWS_S3_ENDPOINT_URL
    )

    storage = StorageService()
    paginator = client.get_paginator('list_objects_v2')
    operation_args = {'Bucket': bucket}
    if prefix:
        operation_args['Prefix'] = prefix

    total_processed = 0
    tmp_dir = Path(settings.BASE_DIR) / 'tmp'
    tmp_dir.mkdir(exist_ok=True)

    for page in paginator.paginate(**operation_args):
        for obj in page.get('Contents', []):
            key = obj.get('Key')
            if not key or not key.lower().endswith('.json'):
                continue

            local_path = tmp_dir / Path(key).name
            try:
                # Download file
                if not storage.fetch_file(key, local_path):
                    logger.error("Failed to download %s", key)
                    continue
                if not local_path.exists():
                    logger.error("File %s missing after download", local_path)
                    continue

                raw = local_path.read_text(encoding='utf-8')
                data = json.loads(raw)
            except Exception as e:
                logger.exception("Error loading JSON from %s: %s", local_path, e)
                continue

            items = data.get('items') or data.get('discounts') or []
            if not items:
                logger.warning("No discount items in '%s'", key)
                local_path.unlink(missing_ok=True)
                continue

            with transaction.atomic():
                for entry in items:
                    # parse entry
                    retailer_name = entry.get('store_name') or entry.get('source') or 'Unknown'
                    retailer, _ = Retailer.objects.get_or_create(
                        name=retailer_name,
                        defaults={'location': None},
                    )

                    category = None
                    cat_name = entry.get('category')
                    if cat_name:
                        category, _ = Category.objects.get_or_create(name=cat_name)

                    def parse_dt(value):
                        if not value:
                            return None
                        dt = parse_datetime(value)
                        if dt and dt.tzinfo is None:
                            dt = timezone.make_aware(dt)
                        return dt

                    valid_from = parse_dt(entry.get('valid_from'))
                    expiration_date = parse_dt(
                        entry.get('valid_until') or entry.get('expiration_date')
                    )

                    # default if no expiration date provided
                    if expiration_date is None:
                        default_exp = timezone.now() + timedelta(days=30)
                        logger.info(
                            "No expiration provided for %s, defaulting to %s", key, default_exp
                        )
                        expiration_date = default_exp

                    loc = None
                    loc_data = entry.get('location')
                    if isinstance(loc_data, (list, tuple)) and len(loc_data) == 2:
                        lat, lon = loc_data
                        loc = Point(float(lon), float(lat))

                    # build discount_code, ensure max length; append hash suffix if truncated
                    raw_code = entry.get('discount_code') or entry.get('url') or key
                    if len(raw_code) > 50:
                        import hashlib
                        suffix = hashlib.md5(raw_code.encode('utf-8')).hexdigest()[:8]
                        discount_code = raw_code[:41] + '_' + suffix
                    else:
                        discount_code = raw_code

                    defaults = {
                        'retailer': retailer,
                        'category': category,
                        'description': entry.get('description') or entry.get('title') or entry.get('name'),
                        'discount_value': entry.get('discount_value') or entry.get('discount_percentage') or 0,
                        'currency': entry.get('currency'),
                        'country': entry.get('country'),
                        'brand': entry.get('brand'),
                        'valid_from': valid_from,
                        'expiration_date': expiration_date,
                        'validity_dates': entry.get('validity_dates'),
                        'address': entry.get('address'),
                        'city': entry.get('city'),
                        'state': entry.get('state'),
                        'postal_code': entry.get('postal_code'),
                        'source': entry.get('source'),
                        'source_id': entry.get('source_id'),
                        'source_url': entry.get('source_url'),
                        'product_id': entry.get('product_id'),
                        'product_url': entry.get('product_url'),
                        'store_name': entry.get('store_name'),
                        'store_id': entry.get('store_id'),
                        'store_url': entry.get('store_url'),
                        'price_per_unit': entry.get('price_per_unit'),
                        'stock_info': entry.get('stock_info'),
                        'location': loc,
                        'error_message': entry.get('error_message'),
                        'url': entry.get('url'),
                        'title': entry.get('title'),
                        'name': entry.get('name'),
                        'size': entry.get('size'),
                        'embedding': entry.get('embedding') or None,
                        'is_active': bool(entry.get('is_processed', True)),
                    }

                    obj, created = Discount.objects.update_or_create(
                        discount_code=discount_code,
                        defaults=defaults,
                    )
                    action = 'Created' if created else 'Updated'
                    logger.info(
                        "%s discount %s (retailer=%s)", action, discount_code, retailer.name
                    )
                    total_processed += 1

            local_path.unlink(missing_ok=True)

    logger.info("Import complete: %d discounts processed", total_processed)
    return total_processed
