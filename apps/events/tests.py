"""
Comprehensive tests for events app.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status

from apps.vendors.models import Vendor
from apps.products.models import Product, Category
from apps.events.models import Event, CampaignLog, EventAnalytics
from apps.events.festivals import get_all_festival_templates

User = get_user_model()


class EventCRUDTestCase(TestCase):
    """Test Event CRUD operations"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create vendor user
        self.vendor_user = User.objects.create_user(
            username='vendor1',
            email='vendor1@test.com',
            password='testpass123',
            role='vendor'
        )
        self.vendor = Vendor.objects.create(
            user=self.vendor_user,
            business_name='Test Business',
            business_email='business@test.com',
            business_phone='1234567890'
        )
        
        # Create another vendor
        self.other_vendor_user = User.objects.create_user(
            username='vendor2',
            email='vendor2@test.com',
            password='testpass123',
            role='vendor'
        )
        self.other_vendor = Vendor.objects.create(
            user=self.other_vendor_user,
            business_name='Other Business',
            business_email='other@test.com',
            business_phone='0987654321'
        )
        
        # Create customer user (non-vendor)
        self.customer_user = User.objects.create_user(
            username='customer1',
            email='customer1@test.com',
            password='testpass123',
            role='customer'
        )
        
        # Create products
        self.category = Category.objects.create(
            name='Test Category',
            vendor=self.vendor
        )
        self.product1 = Product.objects.create(
            vendor=self.vendor,
            name='Product 1',
            description='Test product',
            price=100.00,
            stock_quantity=10,
            sku='PROD1',
            is_active=True
        )
        self.product2 = Product.objects.create(
            vendor=self.vendor,
            name='Product 2',
            description='Test product 2',
            price=200.00,
            stock_quantity=5,
            sku='PROD2',
            is_active=True
        )
        
        # Authenticate as vendor
        self.client.force_authenticate(user=self.vendor_user)
    
    def test_create_event(self):
        """Test creating an event"""
        start_date = timezone.now() + timedelta(days=1)
        end_date = timezone.now() + timedelta(days=7)
        
        data = {
            'name': 'Test Event',
            'description': 'Test description',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'status': 'draft',
            'selected_products': [self.product1.id, self.product2.id]
        }
        
        response = self.client.post('/api/vendor/events/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.count(), 1)
        
        event = Event.objects.first()
        self.assertEqual(event.vendor, self.vendor)
        self.assertEqual(event.name, 'Test Event')
        self.assertEqual(event.status, 'draft')
    
    def test_create_event_invalid_dates(self):
        """Test creating event with invalid dates (end before start)"""
        start_date = timezone.now() + timedelta(days=7)
        end_date = timezone.now() + timedelta(days=1)
        
        data = {
            'name': 'Test Event',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'status': 'draft'
        }
        
        response = self.client.post('/api/vendor/events/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('end_date', response.data)
    
    def test_list_events(self):
        """Test listing events"""
        # Create events
        Event.objects.create(
            vendor=self.vendor,
            name='Event 1',
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=7),
            status='draft'
        )
        Event.objects.create(
            vendor=self.vendor,
            name='Event 2',
            start_date=timezone.now() + timedelta(days=10),
            end_date=timezone.now() + timedelta(days=15),
            status='active'
        )
        # Event for other vendor (should not appear)
        Event.objects.create(
            vendor=self.other_vendor,
            name='Other Event',
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=7),
            status='draft'
        )
        
        response = self.client.get('/api/vendor/events/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_get_event_detail(self):
        """Test getting event details"""
        event = Event.objects.create(
            vendor=self.vendor,
            name='Test Event',
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=7),
            status='draft'
        )
        
        response = self.client.get(f'/api/vendor/events/{event.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Event')
    
    def test_update_event(self):
        """Test updating an event"""
        event = Event.objects.create(
            vendor=self.vendor,
            name='Original name',
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=7),
            status='draft'
        )
        
        data = {
            'name': 'Updated name',
            'description': 'Updated description'
        }
        
        response = self.client.patch(f'/api/vendor/events/{event.id}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        event.refresh_from_db()
        self.assertEqual(event.name, 'Updated name')
    
    def test_delete_event_soft_delete(self):
        """Test soft deleting an event"""
        event = Event.objects.create(
            vendor=self.vendor,
            name='Test Event',
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=7),
            status='draft'
        )
        
        response = self.client.delete(f'/api/vendor/events/{event.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        event.refresh_from_db()
        self.assertTrue(event.is_deleted)
        self.assertIsNotNone(event.deleted_at)
    
    def test_duplicate_event(self):
        """Test duplicating an event"""
        event = Event.objects.create(
            vendor=self.vendor,
            name='Original Event',
            description='Original description',
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=7),
            status='active',
            selected_products=[self.product1.id]
        )
        
        response = self.client.post(f'/api/vendor/events/{event.id}/duplicate/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check duplicate was created
        duplicates = Event.objects.filter(title__contains='Copy')
        self.assertEqual(duplicates.count(), 1)
        
        duplicate = duplicates.first()
        self.assertEqual(duplicate.status, 'draft')
        self.assertEqual(duplicate.vendor, self.vendor)
    
    def test_publish_event(self):
        """Test publishing an event"""
        event = Event.objects.create(
            vendor=self.vendor,
            name='Test Event',
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=7),
            status='draft'
        )
        
        response = self.client.post(f'/api/vendor/events/{event.id}/publish/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        event.refresh_from_db()
        self.assertEqual(event.status, 'active')
        
        # Check analytics entry was created
        analytics = EventAnalytics.objects.filter(event=event).first()
        self.assertIsNotNone(analytics)
    
    def test_vendor_cannot_access_other_vendor_events(self):
        """Test vendor cannot access other vendor's events"""
        other_event = Event.objects.create(
            vendor=self.other_vendor,
            name='Other Event',
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=7),
            status='draft'
        )
        
        response = self.client.get(f'/api/vendor/events/{other_event.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_non_vendor_cannot_access(self):
        """Test non-vendor users cannot access events"""
        self.client.force_authenticate(user=self.customer_user)
        
        response = self.client.get('/api/vendor/events/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class FestivalTemplatesTestCase(TestCase):
    """Test festival templates endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.vendor_user = User.objects.create_user(
            username='vendor1',
            email='vendor1@test.com',
            password='testpass123',
            role='vendor'
        )
        self.vendor = Vendor.objects.create(
            user=self.vendor_user,
            business_name='Test Business',
            business_email='business@test.com',
            business_phone='1234567890'
        )
        
        self.client.force_authenticate(user=self.vendor_user)
    
    def test_list_festival_templates(self):
        """Test listing festival templates"""
        response = self.client.get('/api/vendor/events/festivals/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        templates = response.data
        self.assertGreater(len(templates), 0)
        
        # Check template structure
        template = templates[0]
        self.assertIn('id', template)
        self.assertIn('name', template)
        self.assertIn('preset_message', template)
        self.assertIn('preset_colors', template)
        self.assertIn('hashtags', template)


class ProductRecommendationTestCase(TestCase):
    """Test product recommendations"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.vendor_user = User.objects.create_user(
            username='vendor1',
            email='vendor1@test.com',
            password='testpass123',
            role='vendor'
        )
        self.vendor = Vendor.objects.create(
            user=self.vendor_user,
            business_name='Test Business',
            business_email='business@test.com',
            business_phone='1234567890'
        )
        
        # Create products
        self.category = Category.objects.create(
            name='Test Category',
            vendor=self.vendor
        )
        self.featured_product = Product.objects.create(
            vendor=self.vendor,
            name='Featured Product',
            description='Featured',
            price=100.00,
            stock_quantity=20,
            sku='FEAT1',
            is_active=True,
            is_featured=True
        )
        self.high_stock_product = Product.objects.create(
            vendor=self.vendor,
            name='High Stock Product',
            description='High stock',
            price=200.00,
            stock_quantity=50,
            sku='HIGH1',
            is_active=True,
            is_featured=False
        )
        self.low_stock_product = Product.objects.create(
            vendor=self.vendor,
            name='Low Stock Product',
            description='Low stock',
            price=300.00,
            stock_quantity=2,
            sku='LOW1',
            is_active=True,
            is_featured=False
        )
        
        self.client.force_authenticate(user=self.vendor_user)
    
    def test_get_product_recommendations(self):
        """Test getting product recommendations"""
        response = self.client.get('/api/vendor/events/recommend-products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        products = response.data
        self.assertGreater(len(products), 0)
        
        # Check product structure
        product = products[0]
        self.assertIn('id', product)
        self.assertIn('name', product)
        self.assertIn('price', product)
        self.assertIn('is_in_stock', product)
        
        # Featured products should be first
        if len(products) > 0:
            self.assertEqual(products[0]['id'], self.featured_product.id)


class CampaignLoggingTestCase(TestCase):
    """Test campaign logging"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.vendor_user = User.objects.create_user(
            username='vendor1',
            email='vendor1@test.com',
            password='testpass123',
            role='vendor'
        )
        self.vendor = Vendor.objects.create(
            user=self.vendor_user,
            business_name='Test Business',
            business_email='business@test.com',
            business_phone='1234567890'
        )
        
        self.event = Event.objects.create(
            vendor=self.vendor,
            name='Test Event',
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=7),
            status='active'
        )
        
        self.client.force_authenticate(user=self.vendor_user)
    
    def test_log_campaign(self):
        """Test logging a campaign"""
        data = {
            'message_text': 'Test campaign message',
            'poster_url': 'https://example.com/poster.png',
            'sent_to_phone': '+1234567890',
            'status': 'sent'
        }
        
        response = self.client.post(
            f'/api/vendor/events/{self.event.id}/campaign/send/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check campaign log was created
        campaign_log = CampaignLog.objects.first()
        self.assertIsNotNone(campaign_log)
        self.assertEqual(campaign_log.event, self.event)
        self.assertEqual(campaign_log.message_text, 'Test campaign message')
        self.assertEqual(campaign_log.status, 'sent')


class AnalyticsTestCase(TestCase):
    """Test analytics endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        
        self.vendor_user = User.objects.create_user(
            username='vendor1',
            email='vendor1@test.com',
            password='testpass123',
            role='vendor'
        )
        self.vendor = Vendor.objects.create(
            user=self.vendor_user,
            business_name='Test Business',
            business_email='business@test.com',
            business_phone='1234567890'
        )
        
        self.event = Event.objects.create(
            vendor=self.vendor,
            name='Test Event',
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=7),
            status='active'
        )
        
        self.client.force_authenticate(user=self.vendor_user)
    
    def test_get_analytics(self):
        """Test getting analytics"""
        # Create analytics entry
        EventAnalytics.objects.create(
            event=self.event,
            date=timezone.now().date(),
            views=10,
            clicks=5,
            shares=2,
            leads=1
        )
        
        response = self.client.get(f'/api/vendor/events/{self.event.id}/analytics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        self.assertIn('total_views', data)
        self.assertIn('total_clicks', data)
        self.assertIn('daily_breakdown', data)
    
    def test_update_analytics(self):
        """Test updating analytics"""
        today = timezone.now().date()
        data = {
            'date': today.isoformat(),
            'views': 5,
            'clicks': 3,
            'shares': 1,
            'leads': 0
        }
        
        response = self.client.post(
            f'/api/vendor/events/{self.event.id}/analytics/update/',
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check analytics was updated
        analytics = EventAnalytics.objects.get(event=self.event, date=today)
        self.assertEqual(analytics.views, 5)
        self.assertEqual(analytics.clicks, 3)


class PermissionTestCase(TestCase):
    """Test permissions"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create vendor
        self.vendor_user = User.objects.create_user(
            username='vendor1',
            email='vendor1@test.com',
            password='testpass123',
            role='vendor'
        )
        self.vendor = Vendor.objects.create(
            user=self.vendor_user,
            business_name='Test Business',
            business_email='business@test.com',
            business_phone='1234567890'
        )
        
        # Create customer
        self.customer_user = User.objects.create_user(
            username='customer1',
            email='customer1@test.com',
            password='testpass123',
            role='customer'
        )
    
    def test_unauthenticated_access_denied(self):
        """Test unauthenticated users cannot access"""
        self.client.force_authenticate(user=None)
        
        response = self.client.get('/api/vendor/events/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_customer_cannot_access(self):
        """Test customers cannot access vendor endpoints"""
        self.client.force_authenticate(user=self.customer_user)
        
        response = self.client.get('/api/vendor/events/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_vendor_can_access(self):
        """Test vendors can access"""
        self.client.force_authenticate(user=self.vendor_user)
        
        response = self.client.get('/api/vendor/events/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
