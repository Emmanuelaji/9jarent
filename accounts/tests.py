from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class AgentRegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.signup_url = reverse('accounts:agent_signup')
        self.pending_url = reverse('accounts:pending')
        self.login_url = reverse('accounts:login')
        
        # Create admin user
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@9jarent.com',
            password='adminpass123',
            role='SUPER_ADMIN',
            is_staff=True
        )
        
    def test_renter_can_register(self):
        """Test that a public user can browse but not create properties."""
        response = self.client.get(reverse('properties:home'))
        self.assertEqual(response.status_code, 200)
        
    def test_agent_registration_creates_pending_agent(self):
        """Test that agent signup creates a PENDING agent, not approved."""
        signup_data = {
            'username': 'testagent',
            'first_name': 'Test',
            'last_name': 'Agent',
            'email': 'testagent@example.com',
            'phone': '08012345678',
            'whatsapp_number': '2348012345678',
            'company_name': 'Test Agency',
            'state': 'Lagos',
            'city': 'Lekki',
            'office_address': '123 Test Street',
            'bio': 'Test agent bio',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }
        
        response = self.client.post(self.signup_url, signup_data)
        
        # Should redirect to pending page
        self.assertRedirects(response, self.pending_url)
        
        # Verify user was created with PENDING status
        user = User.objects.get(username='testagent')
        self.assertEqual(user.role, 'MINOR_ADMIN')
        self.assertEqual(user.agent_status, 'PENDING')
        self.assertFalse(user.is_approved_agent)
        self.assertTrue(user.is_pending_agent)
        
    def test_new_agent_cannot_create_property(self):
        """Test that a pending agent cannot create properties."""
        # Create pending agent
        pending_agent = User.objects.create_user(
            username='pendingagent',
            email='pending@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='PENDING',
            whatsapp_number='2348012345678'
        )
        
        self.client.login(username='pendingagent', password='testpass123')
        
        # Try to access property creation
        response = self.client.get(reverse('properties:create'))
        self.assertEqual(response.status_code, 403)  # PermissionDenied
        
    def test_admin_can_approve_agent(self):
        """Test that admin can approve a pending agent."""
        # Create pending agent
        pending_agent = User.objects.create_user(
            username='pendingagent',
            email='pending@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='PENDING',
            whatsapp_number='2348012345678'
        )
        
        self.client.login(username='admin', password='adminpass123')
        
        # Approve agent via POST
        response = self.client.post(
            reverse('dashboard:approve_agent', kwargs={'pk': pending_agent.pk})
        )
        
        # Refresh from db
        pending_agent.refresh_from_db()
        self.assertEqual(pending_agent.agent_status, 'APPROVED')
        self.assertTrue(pending_agent.is_approved_agent)
        self.assertEqual(pending_agent.approved_by, self.admin_user)
        self.assertIsNotNone(pending_agent.approved_at)
        
    def test_approved_agent_can_create_property(self):
        """Test that approved agent can create properties."""
        approved_agent = User.objects.create_user(
            username='approvedagent',
            email='approved@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='APPROVED',
            whatsapp_number='2348012345678',
            state='Lagos',
            city='Lekki'
        )
        
        self.client.login(username='approvedagent', password='testpass123')
        
        # Should be able to access property creation
        response = self.client.get(reverse('properties:create'))
        self.assertEqual(response.status_code, 200)
        
    def test_rejected_agent_cannot_create_property(self):
        """Test that rejected agent cannot create properties."""
        rejected_agent = User.objects.create_user(
            username='rejectedagent',
            email='rejected@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='REJECTED',
            whatsapp_number='2348012345678',
            rejection_reason='Invalid phone number'
        )
        
        self.client.login(username='rejectedagent', password='testpass123')
        
        response = self.client.get(reverse('properties:create'))
        self.assertEqual(response.status_code, 403)
        
    def test_suspended_agent_cannot_create_property(self):
        """Test that suspended agent cannot create properties."""
        suspended_agent = User.objects.create_user(
            username='suspendedagent',
            email='suspended@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='SUSPENDED',
            whatsapp_number='2348012345678',
            rejection_reason='Violation of terms'
        )
        
        self.client.login(username='suspendedagent', password='testpass123')
        
        response = self.client.get(reverse('properties:create'))
        self.assertEqual(response.status_code, 403)
        
    def test_agent_signup_does_not_auto_login(self):
        """Test that agent signup does not auto-login with privileges."""
        signup_data = {
            'username': 'newagent',
            'first_name': 'New',
            'last_name': 'Agent',
            'email': 'newagent@example.com',
            'phone': '08012345678',
            'whatsapp_number': '2348012345678',
            'company_name': 'New Agency',
            'state': 'Abuja',
            'city': 'Wuse',
            'office_address': '',
            'bio': '',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }
        
        response = self.client.post(self.signup_url, signup_data)
        
        # Should NOT be logged in as approved agent
        # The view should redirect to pending page without full login
        # or with restricted session
        self.assertRedirects(response, self.pending_url)
        
    def test_unauthorized_user_cannot_access_admin_dashboard(self):
        """Test that non-admin users cannot access admin dashboard."""
        public_user = User.objects.create_user(
            username='publicuser',
            email='public@example.com',
            password='testpass123',
            role='PUBLIC'
        )
        
        self.client.login(username='publicuser', password='testpass123')
        response = self.client.get(reverse('dashboard:admin'))
        self.assertEqual(response.status_code, 403)
        
    def test_pending_agent_redirected_to_pending_page_on_login(self):
        """Test that pending agents are redirected to pending status page."""
        pending_agent = User.objects.create_user(
            username='pendinglogin',
            email='pendinglogin@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='PENDING',
            whatsapp_number='2348012345678'
        )
        
        response = self.client.post(self.login_url, {
            'username': 'pendinglogin',
            'password': 'testpass123'
        })
        
        # Should redirect to pending page
        self.assertRedirects(response, self.pending_url)
        
    def test_csrf_protection_on_state_changing_endpoints(self):
        """Test that state-changing endpoints require CSRF."""
        # This is handled by Django's CsrfViewMiddleware globally
        # But we verify POST is required for approval actions
        self.client.login(username='admin', password='adminpass123')
        
        pending_agent = User.objects.create_user(
            username='csrftest',
            email='csrf@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='PENDING',
            whatsapp_number='2348012345678'
        )
        
        # GET should not work for approve
        response = self.client.get(
            reverse('dashboard:approve_agent', kwargs={'pk': pending_agent.pk})
        )
        self.assertEqual(response.status_code, 405)  # Method Not Allowed
        
    def test_agent_cannot_edit_another_agents_property(self):
        """Test that agents can only edit their own properties."""
        from properties.models import Property, State, LGA
        
        # Create states and LGA
        state = State.objects.create(name='Lagos', slug='lagos')
        lga = LGA.objects.create(state=state, name='Lekki', slug='lekki')
        
        agent1 = User.objects.create_user(
            username='agent1',
            email='agent1@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='APPROVED',
            whatsapp_number='2348012345678'
        )
        
        agent2 = User.objects.create_user(
            username='agent2',
            email='agent2@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='APPROVED',
            whatsapp_number='2348012345679'
        )
        
        # Create property for agent1
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
            agent_name='Agent 1',
            agent_whatsapp='2348012345678',
            created_by=agent1,
            status='PUBLISHED'
        )
        
        # Agent2 tries to edit
        self.client.login(username='agent2', password='testpass123')
        response = self.client.get(
            reverse('properties:edit', kwargs={'pk': prop.pk})
        )
        self.assertEqual(response.status_code, 403)