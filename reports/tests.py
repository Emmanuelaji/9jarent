from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from properties.models import Property, State, LGA
from reports.models import Report

User = get_user_model()


class ReportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@9jarent.com',
            password='adminpass123',
            role='SUPER_ADMIN',
            is_staff=True
        )
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

    def test_user_can_report_property(self):
        """User can report a property."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('reports:submit', kwargs={'property_id': self.property.pk}),
            {
                'category': 'fake_listing',
                'description': 'This property does not exist.'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Report.objects.count(), 1)
        report = Report.objects.first()
        self.assertEqual(report.category, 'fake_listing')
        self.assertEqual(report.status, Report.Status.PENDING)

    def test_user_can_report_agent(self):
        """User can report an agent."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('reports:submit_agent', kwargs={'agent_id': self.agent.pk}),
            {
                'category': 'suspicious_agent',
                'description': 'This agent seems suspicious.'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Report.objects.count(), 1)

    def test_admin_can_resolve_report(self):
        """Admin can resolve a report."""
        report = Report.objects.create(
            reporter=self.renter,
            property=self.property,
            category='fake_listing',
            description='Fake listing'
        )
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(
            reverse('dashboard:resolve_report', kwargs={'pk': report.pk}),
            {
                'status': 'resolved',
                'admin_notes': 'Investigated and resolved.'
            }
        )
        report.refresh_from_db()
        self.assertEqual(report.status, Report.Status.RESOLVED)
        self.assertEqual(report.admin_notes, 'Investigated and resolved.')
        self.assertEqual(report.resolved_by, self.admin)

    def test_report_requires_description(self):
        """Report submission requires description."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('reports:submit', kwargs={'property_id': self.property.pk}),
            {
                'category': 'fake_listing',
                'description': ''
            }
        )
        self.assertEqual(response.status_code, 200)  # Form error
        self.assertEqual(Report.objects.count(), 0)

    def test_anonymous_cannot_report(self):
        """Anonymous user cannot submit report."""
        response = self.client.post(
            reverse('reports:submit', kwargs={'property_id': self.property.pk}),
            {
                'category': 'fake_listing',
                'description': 'Fake listing'
            }
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login
