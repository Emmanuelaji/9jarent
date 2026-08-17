from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from properties.models import Property, State, LGA
from inspections.models import InspectionRequest

User = get_user_model()


class InspectionWorkflowTests(TestCase):
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

    def test_renter_can_request_inspection(self):
        """Renter can request inspection for published property."""
        self.client.login(username='renter', password='testpass123')
        future_date = (timezone.now().date() + timedelta(days=3)).strftime('%Y-%m-%d')
        response = self.client.post(
            reverse('inspections:request', kwargs={'property_id': self.property.pk}),
            {
                'requested_date': future_date,
                'requested_time': '10:00',
                'renter_message': 'I would like to inspect this property.'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(InspectionRequest.objects.count(), 1)

    def test_agent_can_accept_inspection(self):
        """Agent can accept inspection request."""
        inspection = InspectionRequest.objects.create(
            property=self.property,
            renter=self.renter,
            agent=self.agent,
            requested_date=timezone.now().date() + timedelta(days=3),
            requested_time='10:00',
            status=InspectionRequest.Status.PENDING
        )
        self.client.login(username='agent', password='testpass123')
        response = self.client.post(
            reverse('inspections:accept', kwargs={'pk': inspection.pk})
        )
        inspection.refresh_from_db()
        self.assertEqual(inspection.status, InspectionRequest.Status.ACCEPTED)

    def test_agent_can_decline_inspection(self):
        """Agent can decline inspection request."""
        inspection = InspectionRequest.objects.create(
            property=self.property,
            renter=self.renter,
            agent=self.agent,
            requested_date=timezone.now().date() + timedelta(days=3),
            requested_time='10:00',
            status=InspectionRequest.Status.PENDING
        )
        self.client.login(username='agent', password='testpass123')
        response = self.client.post(
            reverse('inspections:decline', kwargs={'pk': inspection.pk}),
            {'agent_response': 'Sorry, that time does not work for me.'}
        )
        inspection.refresh_from_db()
        self.assertEqual(inspection.status, InspectionRequest.Status.DECLINED)

    def test_renter_sees_inspection_status(self):
        """Renter can view their inspection requests and see status."""
        inspection = InspectionRequest.objects.create(
            property=self.property,
            renter=self.renter,
            agent=self.agent,
            requested_date=timezone.now().date() + timedelta(days=3),
            requested_time='10:00',
            status=InspectionRequest.Status.ACCEPTED
        )
        self.client.login(username='renter', password='testpass123')
        response = self.client.get(reverse('inspections:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Property')
        self.assertContains(response, 'Accepted')

    def test_unrelated_user_cannot_manipulate_inspection(self):
        """User who doesn't own the inspection cannot modify it.

        accept/decline/complete/cancel filter the queryset directly by
        owner (agent=... or renter=...), so an unrelated user gets a 404
        rather than a 403 - this avoids confirming the object even exists
        to someone who has no relationship to it. inspection_detail (viewable
        by renter/agent/admin) uses an explicit permission check and returns
        403 instead, since more than one role is legitimately allowed there.
        """
        inspection = InspectionRequest.objects.create(
            property=self.property,
            renter=self.renter,
            agent=self.agent,
            requested_date=timezone.now().date() + timedelta(days=3),
            requested_time='10:00',
            status=InspectionRequest.Status.PENDING
        )
        self.client.login(username='other_renter', password='testpass123')
        response = self.client.post(
            reverse('inspections:accept', kwargs={'pk': inspection.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_invalid_property_cannot_receive_inspection(self):
        """Cannot request inspection for non-published property."""
        draft_prop = Property.objects.create(
            title='Draft',
            description='Draft property.',
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
        future_date = (timezone.now().date() + timedelta(days=3)).strftime('%Y-%m-%d')
        response = self.client.post(
            reverse('inspections:request', kwargs={'property_id': draft_prop.pk}),
            {
                'requested_date': future_date,
                'requested_time': '10:00'
            }
        )
        self.assertEqual(response.status_code, 404)

    def test_past_date_not_allowed(self):
        """Cannot request inspection for past date."""
        self.client.login(username='renter', password='testpass123')
        past_date = (timezone.now().date() - timedelta(days=1)).strftime('%Y-%m-%d')
        response = self.client.post(
            reverse('inspections:request', kwargs={'property_id': self.property.pk}),
            {
                'requested_date': past_date,
                'requested_time': '10:00'
            }
        )
        self.assertEqual(response.status_code, 200)  # Form error, stays on page
        self.assertEqual(InspectionRequest.objects.count(), 0)

    def test_duplicate_inspection_prevented(self):
        """Cannot create duplicate pending inspection for same property."""
        InspectionRequest.objects.create(
            property=self.property,
            renter=self.renter,
            agent=self.agent,
            requested_date=timezone.now().date() + timedelta(days=3),
            requested_time='10:00',
            status=InspectionRequest.Status.PENDING
        )
        self.client.login(username='renter', password='testpass123')
        future_date = (timezone.now().date() + timedelta(days=4)).strftime('%Y-%m-%d')
        response = self.client.post(
            reverse('inspections:request', kwargs={'property_id': self.property.pk}),
            {
                'requested_date': future_date,
                'requested_time': '14:00'
            }
        )
        self.assertEqual(response.status_code, 302)  # Redirects to existing conversation
        self.assertEqual(InspectionRequest.objects.count(), 1)