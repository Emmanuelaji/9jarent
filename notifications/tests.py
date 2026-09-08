from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from properties.models import Property, State, LGA
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

    def test_redirect_follows_safe_relative_link(self):
        """A normal same-site notification link redirects as expected."""
        notif = Notification.objects.create(
            user=self.renter,
            notification_type=Notification.Type.SYSTEM,
            title='Safe link',
            message='...',
            link='/properties/',
        )
        self.client.login(username='renter', password='testpass123')
        response = self.client.get(reverse('notifications:redirect', kwargs={'pk': notif.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/properties/')
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_redirect_blocks_offsite_link(self):
        """An off-site/protocol-relative link must NOT be followed - this is
        the open-redirect fix for notification_redirect. Even though nothing
        in the current app lets a user set notification.link themselves,
        this is defense-in-depth for whatever writes Notification rows in
        the future."""
        notif = Notification.objects.create(
            user=self.renter,
            notification_type=Notification.Type.SYSTEM,
            title='Malicious link',
            message='...',
            link='//evil.example.com/phishing',
        )
        self.client.login(username='renter', password='testpass123')
        response = self.client.get(reverse('notifications:redirect', kwargs={'pk': notif.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('evil.example.com', response.url)
        self.assertEqual(response.url, reverse('notifications:list'))

    def test_mark_all_read_plain_form_submit_redirects(self):
        """A plain <form method="post"> submit (no X-Requested-With header,
        as in templates/notifications/list.html) must redirect back to an
        HTML page. Previously this view always returned JsonResponse, which
        meant clicking the button navigated the browser to a raw JSON blob
        instead of back to the notifications list."""
        Notification.objects.create(
            user=self.renter, notification_type=Notification.Type.SYSTEM,
            title='A', message='...'
        )
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(reverse('notifications:mark_all_read'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('notifications:list'))
        self.assertEqual(Notification.objects.filter(user=self.renter, is_read=False).count(), 0)

    def test_mark_all_read_ajax_returns_json(self):
        """A fetch()-based caller (X-Requested-With header set) still gets
        the JSON response, for any future JS that wants to mark-all-read
        without a full page reload."""
        Notification.objects.create(
            user=self.renter, notification_type=Notification.Type.SYSTEM,
            title='A', message='...'
        )
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('notifications:mark_all_read'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['unread_count'], 0)