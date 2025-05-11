from .tasks import (
    cleanup_expired_discounts,
    notify_discount_expiration,
    update_discount_status,
    process_location_updates,
    cleanup_invalid_locations,
    sync_merchant_discounts,
    cleanup_merchant_discounts,
    process_discount_updates,
    publish_discount_request,
    handle_websocket_url_callback,
    handle_discount_results,
    process_scraped_url,
    process_redis_urls
)
