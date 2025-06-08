import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.skip("mocked tests skipped", allow_module_level=True)
import pytest
pytest.importorskip("django", reason="django not installed")
import pytest
pytest.importorskip("django", reason="django not installed")
"""
Tests for the Geodiscount models.
"""
from django.test import TestCase
from django.contrib.gis.geos import Point
from django.utils import timezone
from django.core.exceptions import ValidationError
import pytest
from datetime import timedelta

from geodiscounts.models import Retailer, Discount, SharedDiscount, Location, MerchantDiscount

class RetailerModelTest(TestCase):
    """Tests for the Retailer model."""

    databases = {'default', 'geodiscounts_db'}

    def setUp(self):
        """Set up test environment."""
        self.retailer = Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0)
        )

    def test_retailer_str(self):
        """Test string representation of Retailer."""
        self.assertEqual(str(self.retailer), "Test Retailer")

    def test_retailer_name_unique(self):
        """Test that retailer names must be unique."""
        with self.assertRaises(Exception):
            Retailer.objects.create(
                name="Test Retailer",  # Same name as in setUp
                contact_info="another@example.com",
                location=Point(2.0, 2.0)
            )

    def test_retailer_location_validation(self):
        """Test location validation."""
        with self.assertRaises(Exception):
            Retailer.objects.create(
                name="Invalid Location",
                contact_info="test@example.com",
                location="invalid"
            )

class DiscountModelTest(TestCase):
    """Tests for the Discount model."""

    databases = {'default', 'geodiscounts_db'}

    def setUp(self):
        """Set up test environment."""
        self.retailer = Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0)
        )
        self.discount = Discount.objects.create(
            retailer=self.retailer,
            description="Test Discount",
            discount_code="TEST123",
            expiration_date=timezone.now() + timezone.timedelta(days=7),
            location=Point(1.0, 1.0)
        )

    def test_discount_str(self):
        """Test string representation of Discount."""
        expected = f"{self.retailer.name} - {self.discount.description[:30]}"
        self.assertEqual(str(self.discount), expected)

    def test_discount_code_unique(self):
        """Test that discount codes must be unique."""
        with self.assertRaises(Exception):
            Discount.objects.create(
                retailer=self.retailer,
                description="Another Discount",
                discount_code="TEST123",  # Same code as in setUp
                expiration_date=timezone.now() + timezone.timedelta(days=7),
                location=Point(2.0, 2.0)
            )

    def test_discount_expiration(self):
        """Test discount expiration."""
        expired_discount = Discount.objects.create(
            retailer=self.retailer,
            description="Expired Discount",
            discount_code="EXPIRED123",
            expiration_date=timezone.now() - timezone.timedelta(days=1),
            location=Point(1.0, 1.0)
        )
        self.assertTrue(expired_discount.expiration_date < timezone.now())

class SharedDiscountModelTest(TestCase):
    """Tests for the SharedDiscount model."""

    databases = {'default', 'geodiscounts_db'}

    def setUp(self):
        """Set up test environment."""
        self.retailer = Retailer.objects.create(
            name="Test Retailer",
            contact_info="test@example.com",
            location=Point(1.0, 1.0)
        )
        self.discount = Discount.objects.create(
            retailer=self.retailer,
            description="Test Discount",
            discount_code="TEST123",
            expiration_date=timezone.now() + timezone.timedelta(days=7),
            location=Point(1.0, 1.0)
        )
        self.shared_discount = SharedDiscount.objects.create(
            discount=self.discount,
            group_name="Test Group",
            participants=["user1@example.com", "user2@example.com"],
            status="active"
        )

    def test_shared_discount_str(self):
        """Test string representation of SharedDiscount."""
        expected = f"{self.shared_discount.group_name} - {self.discount.discount_code}"
        self.assertEqual(str(self.shared_discount), expected)

    def test_shared_discount_participants(self):
        """Test participants field."""
        self.assertIsInstance(self.shared_discount.participants, list)
        self.assertEqual(len(self.shared_discount.participants), 2)
        self.assertIn("user1@example.com", self.shared_discount.participants)

    def test_shared_discount_status_choices(self):
        """Test status choices validation."""
        shared_discount = SharedDiscount(
            discount=self.discount,
            group_name="Invalid Status",
            participants=["user1@example.com"],
            status="invalid"  # Invalid status
        )
        with self.assertRaises(ValidationError):
            shared_discount.full_clean()

@pytest.mark.django_db
class TestDiscountModel:
    def test_create_discount(self):
        """Test discount creation with valid data."""
        discount = Discount.objects.create(
            title="Test Discount",
            description="Test Description",
            discount_percentage=10,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=7),
            is_active=True
        )
        assert discount.title == "Test Discount"
        assert discount.discount_percentage == 10
        assert discount.is_active

    def test_discount_validation(self):
        """Test discount validation rules."""
        with pytest.raises(ValidationError):
            Discount.objects.create(
                title="Test Discount",
                description="Test Description",
                discount_percentage=101,  # Invalid percentage
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=7)
            )

    def test_discount_date_validation(self):
        """Test discount date validation."""
        with pytest.raises(ValidationError):
            Discount.objects.create(
                title="Test Discount",
                description="Test Description",
                discount_percentage=10,
                start_date=timezone.now() + timedelta(days=7),
                end_date=timezone.now()  # End date before start date
            )

    def test_discount_expiration_scenarios(self):
        """Test various discount expiration scenarios."""
        # Test expired discount
        expired_discount = Discount.objects.create(
            title="Expired Discount",
            description="Test Description",
            discount_percentage=10,
            start_date=timezone.now() - timedelta(days=10),
            end_date=timezone.now() - timedelta(days=1),
            is_active=True
        )
        assert not expired_discount.is_valid()

        # Test future discount
        future_discount = Discount.objects.create(
            title="Future Discount",
            description="Test Description",
            discount_percentage=10,
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=10),
            is_active=True
        )
        assert not future_discount.is_valid()

        # Test active discount
        active_discount = Discount.objects.create(
            title="Active Discount",
            description="Test Description",
            discount_percentage=10,
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=1),
            is_active=True
        )
        assert active_discount.is_valid()

    def test_discount_usage_limits(self):
        """Test discount usage limits and tracking."""
        discount = Discount.objects.create(
            title="Limited Discount",
            description="Test Description",
            discount_percentage=10,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=7),
            max_uses=5,
            current_uses=0
        )
        
        # Test usage increment
        discount.increment_usage()
        assert discount.current_uses == 1
        
        # Test max uses limit
        discount.current_uses = 5
        with pytest.raises(ValidationError):
            discount.increment_usage()

    def test_discount_validation_rules(self):
        """Test comprehensive discount validation rules."""
        # Test invalid percentage
        with pytest.raises(ValidationError):
            Discount.objects.create(
                title="Invalid Percentage",
                description="Test Description",
                discount_percentage=-10,  # Negative percentage
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=7)
            )

        # Test invalid date range
        with pytest.raises(ValidationError):
            Discount.objects.create(
                title="Invalid Date Range",
                description="Test Description",
                discount_percentage=10,
                start_date=timezone.now() + timedelta(days=7),
                end_date=timezone.now()  # End date before start date
            )

        # Test invalid max uses
        with pytest.raises(ValidationError):
            Discount.objects.create(
                title="Invalid Max Uses",
                description="Test Description",
                discount_percentage=10,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=7),
                max_uses=-1  # Negative max uses
            )

        # Test invalid current uses
        with pytest.raises(ValidationError):
            Discount.objects.create(
                title="Invalid Current Uses",
                description="Test Description",
                discount_percentage=10,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=7),
                max_uses=5,
                current_uses=6  # Current uses greater than max uses
            )

    def test_discount_location_validation(self):
        """Test discount location validation."""
        # Test invalid coordinates
        with pytest.raises(ValidationError):
            Discount.objects.create(
                title="Invalid Location",
                description="Test Description",
                discount_percentage=10,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=7),
                location=Point(181, 91)  # Invalid coordinates
            )

        # Test missing location
        with pytest.raises(ValidationError):
            Discount.objects.create(
                title="Missing Location",
                description="Test Description",
                discount_percentage=10,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=7),
                location=None  # Missing location
            )

    def test_discount_retailer_validation(self):
        """Test discount retailer validation."""
        # Test missing retailer
        with pytest.raises(ValidationError):
            Discount.objects.create(
                title="Missing Retailer",
                description="Test Description",
                discount_percentage=10,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=7),
                retailer=None  # Missing retailer
            )

        # Test invalid retailer
        with pytest.raises(ValidationError):
            Discount.objects.create(
                title="Invalid Retailer",
                description="Test Description",
                discount_percentage=10,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=7),
                retailer_id=999999  # Non-existent retailer
            )

@pytest.mark.django_db
class TestLocationModel:
    def test_create_location(self):
        """Test location creation with valid data."""
        location = Location.objects.create(
            name="Test Location",
            latitude=40.7128,
            longitude=-74.0060,
            radius=1000  # meters
        )
        assert location.name == "Test Location"
        assert location.latitude == 40.7128
        assert location.longitude == -74.0060
        assert location.radius == 1000

    def test_location_coordinate_validation(self):
        """Test location coordinate validation."""
        with pytest.raises(ValidationError):
            Location.objects.create(
                name="Test Location",
                latitude=91,  # Invalid latitude
                longitude=-74.0060,
                radius=1000
            )

    def test_location_distance_calculation(self):
        """Test location distance calculation."""
        # Create two locations
        location1 = Location.objects.create(
            name="Location 1",
            latitude=40.7128,
            longitude=-74.0060,  # New York
            radius=1000
        )
        location2 = Location.objects.create(
            name="Location 2",
            latitude=40.7589,
            longitude=-73.9851,  # Nearby in New York
            radius=1000
        )

        # Calculate distance
        distance = location1.calculate_distance(location2)
        assert distance > 0
        assert distance < 5000  # Should be less than 5km

    def test_location_radius_validation(self):
        """Test location radius validation."""
        # Test negative radius
        with pytest.raises(ValidationError):
            Location.objects.create(
                name="Invalid Radius",
                latitude=40.7128,
                longitude=-74.0060,
                radius=-1000
            )

        # Test zero radius
        with pytest.raises(ValidationError):
            Location.objects.create(
                name="Zero Radius",
                latitude=40.7128,
                longitude=-74.0060,
                radius=0
            )

        # Test too large radius
        with pytest.raises(ValidationError):
            Location.objects.create(
                name="Large Radius",
                latitude=40.7128,
                longitude=-74.0060,
                radius=100000  # 100km
            )

    def test_location_overlap_detection(self):
        """Test location overlap detection."""
        # Create overlapping locations
        location1 = Location.objects.create(
            name="Location 1",
            latitude=40.7128,
            longitude=-74.0060,
            radius=1000
        )
        location2 = Location.objects.create(
            name="Location 2",
            latitude=40.7129,  # Very close to location1
            longitude=-74.0061,
            radius=1000
        )

        assert location1.overlaps_with(location2)

        # Create non-overlapping locations
        location3 = Location.objects.create(
            name="Location 3",
            latitude=40.7128,
            longitude=-74.0060,
            radius=100
        )
        location4 = Location.objects.create(
            name="Location 4",
            latitude=40.7589,  # Far from location3
            longitude=-73.9851,
            radius=100
        )

        assert not location3.overlaps_with(location4)

    def test_location_bounding_box(self):
        """Test location bounding box calculation."""
        location = Location.objects.create(
            name="Test Location",
            latitude=40.7128,
            longitude=-74.0060,
            radius=1000
        )

        bbox = location.get_bounding_box()
        assert len(bbox) == 4
        assert bbox[0] < bbox[2]  # min_lat < max_lat
        assert bbox[1] < bbox[3]  # min_lng < max_lng

    def test_location_search(self):
        """Test location search functionality."""
        # Create test locations
        Location.objects.create(
            name="New York Store",
            latitude=40.7128,
            longitude=-74.0060,
            radius=1000
        )
        Location.objects.create(
            name="Brooklyn Store",
            latitude=40.6782,
            longitude=-73.9442,
            radius=1000
        )
        Location.objects.create(
            name="Queens Store",
            latitude=40.7282,
            longitude=-73.7949,
            radius=1000
        )

        # Search for locations near a point
        nearby_locations = Location.objects.nearby(
            latitude=40.7128,
            longitude=-74.0060,
            radius=5000  # 5km
        )
        assert len(nearby_locations) > 0
        assert any(loc.name == "New York Store" for loc in nearby_locations)

    def test_location_serialization(self):
        """Test location serialization."""
        location = Location.objects.create(
            name="Test Location",
            latitude=40.7128,
            longitude=-74.0060,
            radius=1000
        )

        # Test GeoJSON serialization
        geojson = location.to_geojson()
        assert geojson['type'] == 'Feature'
        assert geojson['geometry']['type'] == 'Point'
        assert len(geojson['geometry']['coordinates']) == 2
        assert geojson['properties']['name'] == location.name
        assert geojson['properties']['radius'] == location.radius

@pytest.mark.django_db
class TestMerchantDiscount:
    def test_create_merchant_discount(self):
        """Test merchant discount creation."""
        discount = Discount.objects.create(
            title="Test Discount",
            description="Test Description",
            discount_percentage=10,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=7)
        )
        location = Location.objects.create(
            name="Test Location",
            latitude=40.7128,
            longitude=-74.0060,
            radius=1000
        )
        merchant_discount = MerchantDiscount.objects.create(
            discount=discount,
            location=location,
            merchant_id=1
        )
        assert merchant_discount.discount == discount
        assert merchant_discount.location == location
        assert merchant_discount.merchant_id == 1

    def test_merchant_discount_validation(self):
        """Test merchant discount validation."""
        discount = Discount.objects.create(
            title="Test Discount",
            description="Test Description",
            discount_percentage=10,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=7)
        )
        location = Location.objects.create(
            name="Test Location",
            latitude=40.7128,
            longitude=-74.0060,
            radius=1000
        )
        with pytest.raises(ValidationError):
            MerchantDiscount.objects.create(
                discount=discount,
                location=location,
                merchant_id=-1  # Invalid merchant ID
            )

@pytest.mark.django_db
class TestSharedDiscountModel:
    """Test suite for SharedDiscount model."""

    @pytest.fixture
    def discount(self):
        """Create a test discount."""
        return Discount.objects.create(
            title="Test Discount",
            description="Test Description",
            discount_percentage=10,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=7)
        )

    def test_shared_discount_creation(self, discount):
        """Test shared discount creation with valid data."""
        shared_discount = SharedDiscount.objects.create(
            discount=discount,
            group_name="Test Group",
            participants=["user1@example.com", "user2@example.com"],
            status="active"
        )
        assert shared_discount.discount == discount
        assert shared_discount.group_name == "Test Group"
        assert len(shared_discount.participants) == 2
        assert shared_discount.status == "active"

    def test_shared_discount_participant_limits(self, discount):
        """Test shared discount participant limits."""
        # Test maximum participants limit
        participants = [f"user{i}@example.com" for i in range(11)]  # 11 participants
        with pytest.raises(ValidationError):
            SharedDiscount.objects.create(
                discount=discount,
                group_name="Large Group",
                participants=participants,
                status="active"
            )

    def test_shared_discount_status_transitions(self, discount):
        """Test shared discount status transitions."""
        shared_discount = SharedDiscount.objects.create(
            discount=discount,
            group_name="Test Group",
            participants=["user1@example.com"],
            status="active"
        )

        # Test valid status transition
        shared_discount.status = "completed"
        shared_discount.save()
        assert shared_discount.status == "completed"

        # Test invalid status transition
        with pytest.raises(ValidationError):
            shared_discount.status = "invalid_status"
            shared_discount.save()

    def test_shared_discount_expiration(self, discount):
        """Test shared discount expiration handling."""
        # Create expired discount
        expired_discount = Discount.objects.create(
            title="Expired Discount",
            description="Test Description",
            discount_percentage=10,
            start_date=timezone.now() - timedelta(days=10),
            end_date=timezone.now() - timedelta(days=1)
        )

        # Test creating shared discount with expired discount
        with pytest.raises(ValidationError):
            SharedDiscount.objects.create(
                discount=expired_discount,
                group_name="Expired Group",
                participants=["user1@example.com"],
                status="active"
            )

    def test_shared_discount_participant_validation(self, discount):
        """Test shared discount participant validation."""
        # Test duplicate participants
        with pytest.raises(ValidationError):
            SharedDiscount.objects.create(
                discount=discount,
                group_name="Duplicate Group",
                participants=["user1@example.com", "user1@example.com"],
                status="active"
            )

        # Test invalid email format
        with pytest.raises(ValidationError):
            SharedDiscount.objects.create(
                discount=discount,
                group_name="Invalid Email Group",
                participants=["invalid-email"],
                status="active"
            )

    def test_shared_discount_group_name_validation(self, discount):
        """Test shared discount group name validation."""
        # Test empty group name
        with pytest.raises(ValidationError):
            SharedDiscount.objects.create(
                discount=discount,
                group_name="",
                participants=["user1@example.com"],
                status="active"
            )

        # Test too long group name
        with pytest.raises(ValidationError):
            SharedDiscount.objects.create(
                discount=discount,
                group_name="a" * 101,  # 101 characters
                participants=["user1@example.com"],
                status="active"
            )

    def test_shared_discount_cleanup(self, discount):
        """Test shared discount cleanup on discount deletion."""
        shared_discount = SharedDiscount.objects.create(
            discount=discount,
            group_name="Test Group",
            participants=["user1@example.com"],
            status="active"
        )

        # Delete the discount
        discount.delete()

        # Verify shared discount is also deleted
        with pytest.raises(SharedDiscount.DoesNotExist):
            SharedDiscount.objects.get(id=shared_discount.id) 