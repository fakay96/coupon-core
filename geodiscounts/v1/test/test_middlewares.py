"""
Tests for the ClientIPMiddleware class.

This middleware extracts the client's IP address from the incoming request
and attaches it to the `request` object as `request.client_ip`. The tests
verify that the middleware correctly handles different IP extraction scenarios.


"""

from django.test import RequestFactory, TestCase

from coupon_core.custom_middlewares.userlocation_middleware import \
    ClientIPMiddleware


class ClientIPMiddlewareTest(TestCase):
    """
    Tests for the ClientIPMiddleware class.
    """

    def setUp(self) -> None:
        """
        Sets up the middleware instance and request factory for testing.
        """
        self.middleware = ClientIPMiddleware(lambda request: None)

    def test_client_ip_from_x_forwarded_for(self):
        """
        Test case for extracting the client's IP address from the `X-Forwarded-For` header.

        Expected Behavior:
        - The first IP in the `X-Forwarded-For` header should be set as `request.client_ip`.
        """
        request = RequestFactory().get(
            "/", HTTP_X_FORWARDED_FOR="192.168.1.1, 10.0.0.1"
        )
        self.middleware(request)
        self.assertEqual(request.client_ip, "192.168.1.1")

    def test_client_ip_from_remote_addr(self):
        """
        Test case for extracting the client's IP address from the `REMOTE_ADDR` field.

        Expected Behavior:
        - The IP address in `REMOTE_ADDR` should be set as `request.client_ip`
          when the `X-Forwarded-For` header is not present.
        """
        request = RequestFactory().get("/", REMOTE_ADDR="127.0.0.1")
        self.middleware(request)
        self.assertEqual(request.client_ip, "127.0.0.1")
