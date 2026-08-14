from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from properties.models import Property, State, LGA
from messaging.models import Conversation, Message

User = get_user_model()


class MessagingSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.agent = User.objects.create_user(
            username='agent',
            email='agent@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='APPROVED',
            whatsapp_number='2348012345678'
        )
        self.renter = User.objects.create_user(
            username='renter',
            email='renter@example.com',
            password='testpass123',
            role='PUBLIC'
        )
        self.other_renter = User.objects.create_user(
            username='other_renter',
            email='other@example.com',
            password='testpass123',
            role='PUBLIC'
        )
        self.state = State.objects.create(name='Lagos', slug='lagos')
        self.lga = LGA.objects.create(state=self.state, name='Lekki', slug='lekki')
        self.property = Property.objects.create(
            title='Test Property',
            description='A test property with enough description text.',
            price=500000,
            state=self.state,
            lga=self.lga,
            area='Test Area',
            property_type='3-Bedroom Flat',
            bedrooms=3,
            bathrooms=2,
            agent_name='Agent',
            agent_whatsapp='2348012345678',
            created_by=self.agent,
            status='PUBLISHED'
        )
        self.conversation = Conversation.objects.create(
            property=self.property,
            renter=self.renter,
            agent=self.agent
        )

    def test_renter_can_start_conversation(self):
        """Renter can start a conversation about a published property."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('messaging:start', kwargs={'property_id': self.property.pk})
        )
        self.assertEqual(response.status_code, 302)

    def test_renter_can_message_agent(self):
        """Renter can send message in conversation."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('messaging:detail', kwargs={'pk': self.conversation.pk}),
            {'message': 'Hello, is this still available?'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Message.objects.count(), 1)

    def test_agent_can_reply(self):
        """Agent can reply to renter's message."""
        Message.objects.create(
            conversation=self.conversation,
            sender=self.renter,
            message='Hello, is this still available?'
        )
        self.client.login(username='agent', password='testpass123')
        response = self.client.post(
            reverse('messaging:detail', kwargs={'pk': self.conversation.pk}),
            {'message': 'Yes, it is still available!'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Message.objects.count(), 2)

    def test_unrelated_user_cannot_access_conversation(self):
        """User not part of conversation cannot access it."""
        self.client.login(username='other_renter', password='testpass123')
        response = self.client.get(
            reverse('messaging:detail', kwargs={'pk': self.conversation.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_agent_cannot_message_own_property(self):
        """Agent cannot start conversation about their own property."""
        self.client.login(username='agent', password='testpass123')
        response = self.client.post(
            reverse('messaging:start', kwargs={'property_id': self.property.pk})
        )
        self.assertEqual(response.status_code, 302)
        # Should redirect with error message

    def test_conversation_requires_post(self):
        """Starting conversation requires POST."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.get(
            reverse('messaging:start', kwargs={'property_id': self.property.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_unpublished_property_cannot_be_messaged(self):
        """Cannot start conversation about unpublished property."""
        draft_prop = Property.objects.create(
            title='Draft Prop',
            description='A draft property.',
            price=500000,
            state=self.state,
            lga=self.lga,
            area='Draft',
            property_type='3-Bedroom Flat',
            bedrooms=3,
            bathrooms=2,
            agent_name='Agent',
            agent_whatsapp='2348012345678',
            created_by=self.agent,
            status='DRAFT'
        )
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('messaging:start', kwargs={'property_id': draft_prop.pk})
        )
        self.assertEqual(response.status_code, 404)
