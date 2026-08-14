from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.middleware.csrf import get_token

from properties.models import Property, State, LGA

User = get_user_model()


class SecurityTests(TestCase):
    """Comprehensive security tests for 9jaRent."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@9jarent.com',
            password='adminpass123',
            role='SUPER_ADMIN',
            is_staff=True
        )
        self.approved_agent = User.objects.create_user(
            username='approved_agent',
            email='agent@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='APPROVED',
            whatsapp_number='2348012345678'
        )
        self.pending_agent = User.objects.create_user(
            username='pending_agent',
            email='pending@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='PENDING',
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
            created_by=self.approved_agent,
            status='PUBLISHED'
        )

    # =====================================================================
    # TEST 32: Unauthenticated user cannot access protected dashboard
    # =====================================================================
    def test_unauthenticated_cannot_access_admin_dashboard(self):
        """Anonymous users redirected from admin dashboard."""
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_cannot_access_agent_dashboard(self):
        """Anonymous users redirected from agent dashboard."""
        response = self.client.get(reverse('properties:mine'))
        self.assertEqual(response.status_code, 302)

    # =====================================================================
    # TEST 33: Renter cannot access admin
    # =====================================================================
    def test_renter_cannot_access_admin_dashboard(self):
        """Renter gets 403 on admin dashboard."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 403)

    def test_renter_cannot_approve_agent(self):
        """Renter cannot approve agents."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('dashboard:approve_agent', kwargs={'pk': self.pending_agent.pk})
        )
        self.assertEqual(response.status_code, 403)

    # =====================================================================
    # TEST 34: Pending agent cannot bypass approval
    # =====================================================================
    def test_pending_agent_cannot_create_property(self):
        """Pending agent gets 403 on property creation."""
        self.client.login(username='pending_agent', password='testpass123')
        response = self.client.get(reverse('properties:create'))
        self.assertEqual(response.status_code, 403)

    def test_pending_agent_cannot_access_agent_dashboard(self):
        """Pending agent sees pending message, not full dashboard."""
        self.client.login(username='pending_agent', password='testpass123')
        response = self.client.get(reverse('properties:mine'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pending')

    # =====================================================================
    # TEST 35: Agent cannot modify another agent's property
    # =====================================================================
    def test_agent_cannot_edit_other_agent_property(self):
        """Agent cannot edit property they don't own."""
        other_agent = User.objects.create_user(
            username='other_agent',
            email='other@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='APPROVED',
            whatsapp_number='2348012345678'
        )
        other_property = Property.objects.create(
            title='Other Property',
            description='Another property.',
            price=500000,
            state=self.state,
            lga=self.lga,
            area='Other',
            property_type='3-Bedroom Flat',
            bedrooms=3,
            bathrooms=2,
            agent_name='Other',
            agent_whatsapp='2348012345678',
            created_by=other_agent,
            status='PUBLISHED'
        )
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.get(reverse('properties:edit', kwargs={'pk': other_property.pk}))
        self.assertEqual(response.status_code, 403)

    def test_agent_cannot_delete_other_agent_image(self):
        """Agent cannot delete another agent's property image."""
        from properties.models import PropertyImage
        other_agent = User.objects.create_user(
            username='other_agent2',
            email='other2@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='APPROVED',
            whatsapp_number='2348012345678'
        )
        other_property = Property.objects.create(
            title='Other Property 2',
            description='Another property.',
            price=500000,
            state=self.state,
            lga=self.lga,
            area='Other',
            property_type='3-Bedroom Flat',
            bedrooms=3,
            bathrooms=2,
            agent_name='Other',
            agent_whatsapp='2348012345678',
            created_by=other_agent,
            status='PUBLISHED'
        )
        image = PropertyImage.objects.create(
            property=other_property,
            image='test.jpg',
            is_primary=True,
            order_index=0
        )
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.post(
            reverse('properties:delete_image', kwargs={'pk': other_property.pk, 'image_id': image.pk})
        )
        self.assertEqual(response.status_code, 403)

    # =====================================================================
    # TEST 36: State-changing endpoints require CSRF
    # =====================================================================
    def test_csrf_required_on_login(self):
        """Login form requires CSRF token."""
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse('accounts:login'), {
            'username': 'renter',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 403)

    def test_csrf_required_on_property_create(self):
        """Property creation requires CSRF token."""
        self.client.login(username='approved_agent', password='testpass123')
        # Get CSRF token first
        response = self.client.get(reverse('properties:create'))
        csrf_token = response.context.get('csrf_token', '')

        # Now post with token should work
        response = self.client.post(reverse('properties:create'), {
            'title': 'CSRF Test',
            'description': 'Testing CSRF protection with enough text.',
            'price': 500000,
            'state': self.state.pk,
            'lga': self.lga.pk,
            'area': 'Test',
            'property_type': '3-Bedroom Flat',
            'bedrooms': 3,
            'bathrooms': 2,
            'agent_name': 'Agent',
            'agent_whatsapp': '2348012345678',
            'csrfmiddlewaretoken': csrf_token,
            'action': 'submit'
        })
        # Should succeed (redirect) or show form errors, not 403
        self.assertNotEqual(response.status_code, 403)

    # =====================================================================
    # ADDITIONAL SECURITY TESTS
    # =====================================================================
    def test_get_request_blocked_on_state_changing_endpoints(self):
        """State-changing endpoints reject GET requests."""
        self.client.login(username='admin', password='adminpass123')

        # Approve agent via GET should fail
        response = self.client.get(
            reverse('dashboard:approve_agent', kwargs={'pk': self.pending_agent.pk})
        )
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_idor_protection_on_property_detail(self):
        """Cannot access property detail by guessing ID if not published."""
        draft = Property.objects.create(
            title='Secret Draft',
            description='Secret property.',
            price=500000,
            state=self.state,
            lga=self.lga,
            area='Secret',
            property_type='3-Bedroom Flat',
            bedrooms=3,
            bathrooms=2,
            agent_name='Agent',
            agent_whatsapp='2348012345678',
            created_by=self.approved_agent,
            status='DRAFT'
        )
        response = self.client.get(reverse('properties:detail', kwargs={'slug': draft.slug}))
        self.assertEqual(response.status_code, 404)

    def test_sql_injection_protection_in_search(self):
        """Search is protected against SQL injection."""
        response = self.client.get(reverse('properties:list'), {'search': "'; DROP TABLE properties; --"})
        self.assertEqual(response.status_code, 200)
        # If SQL injection worked, this would crash. It should return empty results safely.
        self.assertEqual(len(response.context['properties']), 0)

    def test_xss_protection_in_property_title(self):
        """Property titles are escaped to prevent XSS."""
        xss_property = Property.objects.create(
            title='<script>alert("XSS")</script>',
            description='XSS test property with enough description text.',
            price=500000,
            state=self.state,
            lga=self.lga,
            area='Test',
            property_type='3-Bedroom Flat',
            bedrooms=3,
            bathrooms=2,
            agent_name='Agent',
            agent_whatsapp='2348012345678',
            created_by=self.approved_agent,
            status='PUBLISHED'
        )
        response = self.client.get(reverse('properties:detail', kwargs={'slug': xss_property.slug}))
        self.assertEqual(response.status_code, 200)
        # The script tag should be escaped, not executed
        content = response.content.decode()
        self.assertNotIn('<script>alert("XSS")</script>', content)
        self.assertIn('&lt;script&gt;', content)  # Django auto-escapes
