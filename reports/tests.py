from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from properties.models import Property, State, LGA
from .models import Report

User = get_user_model()


class ReportTests(TestCase):
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
        self.state = State.objects.create(name='Lagos', slug='lagos')
        self.lga = LGA.objects.create(state=self.state, name='Lekki', slug='lekki')
        self.property = Property.objects.create(
            title='Test Property',
            description='A test property with enough description text here.',
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

    def test_report_property_requires_login(self):
        """Anonymous users cannot submit reports."""
        response = self.client.get(
            reverse('reports:report_property', kwargs={'property_id': self.property.pk})
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_report_property_success(self):
        """Authenticated user can report a property."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('reports:report_property', kwargs={'property_id': self.property.pk}),
            {
                'category': 'fake_listing',
                'description': 'This property does not exist. I visited the location and found nothing.',
            }
        )
        self.assertEqual(response.status_code, 302)

        report = Report.objects.first()
        self.assertIsNotNone(report)
        self.assertEqual(report.category, 'fake_listing')
        self.assertEqual(report.reporter, self.renter)
        self.assertEqual(report.property, self.property)
        self.assertEqual(report.agent, self.agent)
        self.assertEqual(report.status, Report.Status.PENDING)

    def test_cannot_report_own_property(self):
        """Agents cannot report their own properties."""
        self.client.login(username='agent', password='testpass123')
        response = self.client.post(
            reverse('reports:report_property', kwargs={'property_id': self.property.pk}),
            {
                'category': 'fake_listing',
                'description': 'This is my own property but I am reporting it.',
            }
        )
        self.assertEqual(Report.objects.count(), 0)

    def test_duplicate_report_prevented(self):
        """Users cannot submit duplicate pending reports."""
        Report.objects.create(
            reporter=self.renter,
            property=self.property,
            agent=self.agent,
            category='fake_listing',
            description='First report',
            status=Report.Status.PENDING
        )

        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('reports:report_property', kwargs={'property_id': self.property.pk}),
            {
                'category': 'wrong_price',
                'description': 'This is a duplicate report that should be blocked.',
            }
        )
        self.assertEqual(Report.objects.count(), 1)

    def test_report_agent_success(self):
        """Authenticated user can report an agent."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('reports:report_agent', kwargs={'agent_id': self.agent.pk}),
            {
                'category': 'suspicious_agent',
                'description': 'This agent asked me to pay outside the platform.',
            }
        )
        self.assertEqual(response.status_code, 302)

        report = Report.objects.first()
        self.assertIsNotNone(report)
        self.assertEqual(report.category, 'suspicious_agent')
        self.assertEqual(report.agent, self.agent)
        self.assertIsNone(report.property)

    def test_report_description_minimum_length(self):
        """Reports must have meaningful descriptions."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('reports:report_property', kwargs={'property_id': self.property.pk}),
            {
                'category': 'other',
                'description': 'Too short',
            }
        )
        self.assertEqual(response.status_code, 200)  # Form error, not redirect
        self.assertEqual(Report.objects.count(), 0)

    def test_report_list_admin_access(self):
        """Only admins can access the reports dashboard."""
        # Anonymous
        response = self.client.get(reverse('dashboard:reports'))
        self.assertEqual(response.status_code, 302)

        # Renter
        self.client.login(username='renter', password='testpass123')
        response = self.client.get(reverse('dashboard:reports'))
        self.assertEqual(response.status_code, 403)

        # Admin
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('dashboard:reports'))
        self.assertEqual(response.status_code, 200)
