from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from properties.models import Property, State, LGA
from inspections.models import InspectionRequest
from reports.models import Report

User = get_user_model()


class DashboardAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
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

    def test_admin_can_access_dashboard(self):
        """Admin can access the main dashboard."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')

    def test_agent_cannot_access_dashboard(self):
        """Agents cannot access admin dashboard."""
        self.client.login(username='agent', password='testpass123')
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 403)

    def test_renter_cannot_access_dashboard(self):
        """Renters cannot access admin dashboard."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_access_dashboard(self):
        """Anonymous users are redirected to login."""
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 302)


class DashboardMetricsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@9jarent.com',
            password='adminpass123',
            role='SUPER_ADMIN',
            is_staff=True
        )
        self.state = State.objects.create(name='Lagos', slug='lagos')
        self.lga = LGA.objects.create(state=self.state, name='Lekki', slug='lekki')

    def test_dashboard_shows_property_metrics(self):
        """Dashboard displays property count metrics."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_listings', response.context)

    def test_dashboard_shows_agent_metrics(self):
        """Dashboard displays agent count metrics."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('pending_agents', response.context)
        self.assertIn('approved_agents', response.context)

    def test_dashboard_shows_inspection_metrics(self):
        """Dashboard displays inspection count metrics."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_inspections', response.context)
        self.assertIn('pending_inspections', response.context)

    def test_dashboard_shows_report_metrics(self):
        """Dashboard displays report count metrics."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_reports', response.context)
        self.assertIn('pending_reports', response.context)


class DashboardInspectionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
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

    def test_inspection_list_accessible_by_admin(self):
        """Admin can view inspection list."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('dashboard:inspections_list'))
        self.assertEqual(response.status_code, 200)

    def test_inspection_list_shows_counts(self):
        """Inspection list shows status counts."""
        InspectionRequest.objects.create(
            property=self.property,
            renter=self.renter,
            agent=self.agent,
            requested_date='2026-08-20',
            requested_time='10:00',
            status=InspectionRequest.Status.PENDING
        )
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('dashboard:inspections_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['status_counts']['PENDING'], 1)

    def test_inspection_detail_accessible_by_admin(self):
        """Admin can view inspection detail."""
        inspection = InspectionRequest.objects.create(
            property=self.property,
            renter=self.renter,
            agent=self.agent,
            requested_date='2026-08-20',
            requested_time='10:00',
            status=InspectionRequest.Status.PENDING
        )
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('dashboard:inspection_detail', kwargs={'pk': inspection.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, inspection.property.title)


class DashboardReportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
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

    def test_reports_list_accessible_by_admin(self):
        """Admin can view reports list."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('dashboard:reports_list'))
        self.assertEqual(response.status_code, 200)

    def test_report_detail_accessible_by_admin(self):
        """Admin can view report detail."""
        report = Report.objects.create(
            reporter=self.renter,
            property=self.property,
            agent=self.agent,
            category='fake_listing',
            description='This is a fake listing'
        )
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(
            reverse('dashboard:report_detail', kwargs={'pk': report.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, report.description)
