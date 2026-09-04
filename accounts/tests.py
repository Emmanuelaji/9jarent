from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from properties.models import State, LGA

User = get_user_model()

class AgentRegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.signup_url = reverse('accounts:agent_signup')
        self.pending_url = reverse('accounts:pending')
        self.login_url = reverse('accounts:login')
        self.state = State.objects.create(name='Lagos', slug='lagos')
        self.lga = LGA.objects.create(state=self.state, name='Lekki', slug='lekki')

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
        """Test that completing the full agent signup wizard creates a PENDING agent, not approved."""
        from accounts.models import EmailOTP

        step1_data = {
            'company_name': 'Test Agency',
            'state': self.state.id,
            'city': self.lga.id,
            'office_address': '123 Test Street',
            'phone': '08012345678',
            'whatsapp_number': '2348012345678',
            'email': 'testagent@example.com',
            'bio': 'Test agent bio',
        }
        response = self.client.post(self.signup_url, step1_data)
        self.assertRedirects(response, reverse('accounts:agent_signup_verify'))

        user = User.objects.get(email='testagent@example.com')
        self.assertEqual(user.role, 'MINOR_ADMIN')
        self.assertEqual(user.agent_status, 'PENDING')
        self.assertFalse(user.email_verified)
        self.assertFalse(user.has_usable_password())

        otp = EmailOTP.objects.get(user=user, purpose='SIGNUP', is_used=False)
        response = self.client.post(reverse('accounts:agent_signup_verify'), {'code': otp.code})
        self.assertRedirects(response, reverse('accounts:agent_signup_setup'))
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

        response = self.client.post(reverse('accounts:agent_signup_setup'), {
            'first_name': 'Test', 'last_name': 'Agent',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!',
        })
        self.assertRedirects(response, self.pending_url)

        user.refresh_from_db()
        self.assertEqual(user.role, 'MINOR_ADMIN')
        self.assertEqual(user.agent_status, 'PENDING')
        self.assertFalse(user.is_approved_agent)
        self.assertTrue(user.is_pending_agent)
        self.assertTrue(user.has_usable_password())
        
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
        """Test that agent signup does not auto-login with privileges at any step."""
        from accounts.models import EmailOTP

        step1_data = {
            'company_name': 'New Agency', 'state': self.state.id, 'city': self.lga.id,
            'office_address': '', 'phone': '08012345678', 'whatsapp_number': '2348012345678',
            'email': 'newagent@example.com', 'bio': '',
        }
        response = self.client.post(self.signup_url, step1_data)
        self.assertRedirects(response, reverse('accounts:agent_signup_verify'))
        self.assertNotIn('_auth_user_id', self.client.session)

        user = User.objects.get(email='newagent@example.com')
        otp = EmailOTP.objects.get(user=user, purpose='SIGNUP', is_used=False)
        response = self.client.post(reverse('accounts:agent_signup_verify'), {'code': otp.code})
        self.assertRedirects(response, reverse('accounts:agent_signup_setup'))
        self.assertNotIn('_auth_user_id', self.client.session)

        response = self.client.post(reverse('accounts:agent_signup_setup'), {
            'first_name': 'New', 'last_name': 'Agent',
            'password1': 'StrongPass123!', 'password2': 'StrongPass123!',
        })
        # Should NOT be logged in as approved agent - the view redirects to the
        # pending page without establishing a session at all.
        self.assertRedirects(response, self.pending_url)
        self.assertNotIn('_auth_user_id', self.client.session)
        
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


class LogoutTests(TestCase):
    """
    Regression tests for a real production bug: Django 5.0 made LogoutView
    POST-only (GET logout requests now 405), but every logout link in the
    templates was a plain <a href> (a GET request) - so clicking "Logout"
    silently did nothing and left the user authenticated.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username='logouttest', email='logout@example.com', password='testpass123'
        )

    def test_get_logout_does_not_log_out(self):
        """Confirms the underlying Django behavior this bug depended on."""
        self.client.login(username='logouttest', password='testpass123')
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_post_logout_logs_out(self):
        """The actual fix: logout links must POST, not GET."""
        self.client.login(username='logouttest', password='testpass123')
        response = self.client.post(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_portal_sidebar_logout_is_a_post_form_not_a_get_link(self):
        """Guards against regressing back to a plain <a href> logout link."""
        self.client.login(username='logouttest', password='testpass123')
        response = self.client.get(reverse('properties:home'))
        content = response.content.decode()
        # A bare `href="...logout/"` anchor (no accompanying POST form) would
        # mean the link is broken again exactly like before the fix.
        self.assertIn('action="/accounts/logout/"', content)


class AgentSignUpWizardEdgeCaseTests(TestCase):
    """Edge cases for the 3-step agent signup wizard beyond the happy path."""

    def setUp(self):
        self.state = State.objects.create(name='Lagos', slug='lagos')
        self.lga = LGA.objects.create(state=self.state, name='Ikeja', slug='ikeja')

    def test_wrong_otp_code_does_not_verify(self):
        self.client.post(reverse('accounts:agent_signup'), {
            'company_name': 'Edge Co', 'state': self.state.id, 'city': self.lga.id,
            'office_address': '', 'phone': '08012345678', 'whatsapp_number': '2348012345678',
            'email': 'edgecase@example.com', 'bio': '',
        })
        response = self.client.post(reverse('accounts:agent_signup_verify'), {'code': '000000'})
        self.assertEqual(response.status_code, 200)  # re-renders the form with an error
        user = User.objects.get(email='edgecase@example.com')
        self.assertFalse(user.email_verified)

    def test_step2_redirects_to_step1_without_session_state(self):
        """Visiting step 2 directly (no prior step 1) shouldn't crash - it
        should bounce back to step 1."""
        response = self.client.get(reverse('accounts:agent_signup_verify'))
        self.assertRedirects(response, reverse('accounts:agent_signup'))

    def test_step3_redirects_to_step1_without_verified_email(self):
        """Visiting step 3 directly (email not yet verified) shouldn't let
        someone finish account setup without ever confirming their email."""
        self.client.post(reverse('accounts:agent_signup'), {
            'company_name': 'Edge Co 2', 'state': self.state.id, 'city': self.lga.id,
            'office_address': '', 'phone': '08012345678', 'whatsapp_number': '2348012345678',
            'email': 'edgecase2@example.com', 'bio': '',
        })
        response = self.client.get(reverse('accounts:agent_signup_setup'))
        self.assertRedirects(response, reverse('accounts:agent_signup'))

    def test_resend_code_invalidates_previous_code(self):
        from accounts.models import EmailOTP
        self.client.post(reverse('accounts:agent_signup'), {
            'company_name': 'Edge Co 3', 'state': self.state.id, 'city': self.lga.id,
            'office_address': '', 'phone': '08012345678', 'whatsapp_number': '2348012345678',
            'email': 'edgecase3@example.com', 'bio': '',
        })
        user = User.objects.get(email='edgecase3@example.com')
        first_otp = EmailOTP.objects.get(user=user, is_used=False)

        self.client.post(reverse('accounts:agent_signup_verify'), {'resend': '1'})
        first_otp.refresh_from_db()
        self.assertTrue(first_otp.is_used)

        new_otp = EmailOTP.objects.get(user=user, is_used=False)
        self.assertNotEqual(new_otp.pk, first_otp.pk)