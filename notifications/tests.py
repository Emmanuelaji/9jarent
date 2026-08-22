from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from properties.models import Property, State, LGA
from inspections.models import InspectionRequest
from messaging.models import Conversation, Message
from .models import Notification

User = get_user_model()


class NotificationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.renter = User.objects.create_user(
            username='renter',
            email='renter@example.com',
            password='testpass123',
            role='PUBLIC'
        )
        self.agent = User.objects.create_user(
            username='agent',
            email='agent@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='APPROVED',
            whatsapp_number='2348012345678'
        )
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            role='SUPER_ADMIN',
            is_staff=True
        )

    def test_notification_created_on_inspection_request(self):
        """Test that agent gets notified of new inspection request."""
        state = State.objects.create(name='Lagos', slug='lagos')
        lga = LGA.objects.create(state=state, name='Lekki', slug='lekki')
        prop = Property.objects.create(
            title='Test Property',
            description='A test property with enough description text.',
            price=500000,
            state=state,
            lga=lga,
            area='Test Area',
            property_type='3-Bedroom Flat',
            bedrooms=3,
            bathrooms=2,
            agent_name='Agent',
            agent_whatsapp='2348012345678',
            created_by=self.agent,
            status='PUBLISHED'
        )

        self.client.login(username='renter', password='testpass123')
        from datetime import date, timedelta
        self.client.post(
            reverse('inspections:request', kwargs={'property_id': prop.pk}),
            {
                'requested_date': (date.today() + timedelta(days=3)).isoformat(),
                'requested_time': '10:00',
                'renter_message': 'I want to inspect this property.'
            }
        )

        # Agent should have a notification
        notification = Notification.objects.filter(
            user=self.agent,
            notification_type=Notification.Type.INSPECTION_REQUEST
        ).first()
        self.assertIsNotNone(notification)
        self.assertIn('renter', notification.message.lower())

    def test_notification_created_on_new_message(self):
        """Test that users get notified of new messages."""
        state = State.objects.create(name='Lagos', slug='lagos')
        lga = LGA.objects.create(state=state, name='Lekki', slug='lekki')
        prop = Property.objects.create(
            title='Test Property',
            description='A test property with enough description text.',
            price=500000,
            state=state,
            lga=lga,
            area='Test Area',
            property_type='3-Bedroom Flat',
            bedrooms=3,
            bathrooms=2,
            agent_name='Agent',
            agent_whatsapp='2348012345678',
            created_by=self.agent,
            status='PUBLISHED'
        )

        conversation = Conversation.objects.create(
            property=prop,
            renter=self.renter,
            agent=self.agent
        )

        # Renter sends message
        Message.objects.create(
            conversation=conversation,
            sender=self.renter,
            message='Hello, is this available?'
        )

        # Agent should have notification
        notification = Notification.objects.filter(
            user=self.agent,
            notification_type=Notification.Type.NEW_MESSAGE
        ).first()
        self.assertIsNotNone(notification)

    def test_mark_notification_read(self):
        """Test marking a notification as read."""
        notification = Notification.objects.create(
            user=self.renter,
            notification_type=Notification.Type.SYSTEM,
            title='Test',
            message='Test message'
        )
        self.assertFalse(notification.is_read)

        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('notifications:mark_read', kwargs={'pk': notification.pk})
        )
        self.assertEqual(response.status_code, 200)

        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_unread_count_context_processor(self):
        """Test unread notification count in context."""
        Notification.objects.create(
            user=self.renter,
            notification_type=Notification.Type.SYSTEM,
            title='Unread',
            message='Unread message'
        )

        self.client.login(username='renter', password='testpass123')
        response = self.client.get(reverse('properties:home'))
        self.assertEqual(response.context['unread_notification_count'], 1)
        self.assertTrue(response.context['has_unread_notifications'])

    def test_notification_list_private(self):
        """Test users can only see their own notifications."""
        Notification.objects.create(
            user=self.renter,
            notification_type=Notification.Type.SYSTEM,
            title='Renter Notif',
            message='For renter'
        )
        Notification.objects.create(
            user=self.agent,
            notification_type=Notification.Type.SYSTEM,
            title='Agent Notif',
            message='For agent'
        )

        self.client.login(username='renter', password='testpass123')
        response = self.client.get(reverse('notifications:list'))
        self.assertEqual(response.status_code, 200)
        notifications = list(response.context['notifications'])
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0].title, 'Renter Notif')