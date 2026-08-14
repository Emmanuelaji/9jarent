from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from properties.models import Property, State, LGA, PropertyImage

User = get_user_model()


class PropertyLifecycleTests(TestCase):
    """Test the complete property status lifecycle."""

    def setUp(self):
        self.client = Client()

        # Create users
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
        self.rejected_agent = User.objects.create_user(
            username='rejected_agent',
            email='rejected@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='REJECTED',
            whatsapp_number='2348012345678'
        )
        self.suspended_agent = User.objects.create_user(
            username='suspended_agent',
            email='suspended@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='SUSPENDED',
            whatsapp_number='2348012345678'
        )
        self.renter = User.objects.create_user(
            username='renter',
            email='renter@example.com',
            password='testpass123',
            role='PUBLIC'
        )

        # Create location data
        self.state = State.objects.create(name='Lagos', slug='lagos')
        self.lga = LGA.objects.create(state=self.state, name='Lekki', slug='lekki')

        # Create properties in different statuses
        self.draft_property = Property.objects.create(
            title='Draft Property',
            description='A draft property with enough description text for validation.',
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
            status='DRAFT'
        )

        self.pending_property = Property.objects.create(
            title='Pending Property',
            description='A pending property with enough description text for validation.',
            price=600000,
            state=self.state,
            lga=self.lga,
            area='Test Area 2',
            property_type='2-Bedroom Flat',
            bedrooms=2,
            bathrooms=1,
            agent_name='Agent',
            agent_whatsapp='2348012345678',
            created_by=self.approved_agent,
            status='PENDING_REVIEW'
        )

        self.published_property = Property.objects.create(
            title='Published Property',
            description='A published property with enough description text for validation.',
            price=700000,
            state=self.state,
            lga=self.lga,
            area='Test Area 3',
            property_type='4-Bedroom Duplex',
            bedrooms=4,
            bathrooms=3,
            agent_name='Agent',
            agent_whatsapp='2348012345678',
            created_by=self.approved_agent,
            status='PUBLISHED',
            published_at='2026-01-01'
        )

        self.rejected_property = Property.objects.create(
            title='Rejected Property',
            description='A rejected property with enough description text for validation.',
            price=400000,
            state=self.state,
            lga=self.lga,
            area='Test Area 4',
            property_type='Mini Flat',
            bedrooms=1,
            bathrooms=1,
            agent_name='Agent',
            agent_whatsapp='2348012345678',
            created_by=self.approved_agent,
            status='REJECTED',
            rejection_reason='Insufficient description'
        )

        self.rented_property = Property.objects.create(
            title='Rented Property',
            description='A rented property with enough description text for validation.',
            price=800000,
            state=self.state,
            lga=self.lga,
            area='Test Area 5',
            property_type='5-Bedroom Duplex',
            bedrooms=5,
            bathrooms=4,
            agent_name='Agent',
            agent_whatsapp='2348012345678',
            created_by=self.approved_agent,
            status='RENTED'
        )

        self.archived_property = Property.objects.create(
            title='Archived Property',
            description='An archived property with enough description text for validation.',
            price=300000,
            state=self.state,
            lga=self.lga,
            area='Test Area 6',
            property_type='Self Contained',
            bedrooms=1,
            bathrooms=1,
            agent_name='Agent',
            agent_whatsapp='2348012345678',
            created_by=self.approved_agent,
            status='ARCHIVED'
        )

    # =========================================================================
    # TEST 1: Property starts in correct status
    # =========================================================================
    def test_property_default_status_is_pending_review(self):
        """New property created via form defaults to PENDING_REVIEW."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.post(reverse('properties:create'), {
            'title': 'New Property',
            'description': 'A new property with enough description text for validation to pass.',
            'price': 500000,
            'state': self.state.pk,
            'lga': self.lga.pk,
            'area': 'New Area',
            'property_type': '3-Bedroom Flat',
            'bedrooms': 3,
            'bathrooms': 2,
            'agent_name': 'Test Agent',
            'agent_whatsapp': '2348012345678',
            'action': 'submit'
        })
        # Should redirect after success
        prop = Property.objects.filter(title='New Property').first()
        self.assertIsNotNone(prop)
        self.assertEqual(prop.status, 'PENDING_REVIEW')

    def test_property_can_be_saved_as_draft(self):
        """Agent can save property as DRAFT instead of submitting."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.post(reverse('properties:create'), {
            'title': 'Draft Property New',
            'description': 'A draft property with enough description text for validation to pass.',
            'price': 500000,
            'state': self.state.pk,
            'lga': self.lga.pk,
            'area': 'Draft Area',
            'property_type': '3-Bedroom Flat',
            'bedrooms': 3,
            'bathrooms': 2,
            'agent_name': 'Test Agent',
            'agent_whatsapp': '2348012345678',
            'action': 'draft'
        })
        prop = Property.objects.filter(title='Draft Property New').first()
        self.assertIsNotNone(prop)
        self.assertEqual(prop.status, 'DRAFT')

    # =========================================================================
    # TEST 2: Pending property is not publicly visible
    # =========================================================================
    def test_pending_property_not_in_public_list(self):
        """PENDING_REVIEW properties do not appear in public listings."""
        response = self.client.get(reverse('properties:list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Pending Property')

    def test_draft_property_not_in_public_list(self):
        """DRAFT properties do not appear in public listings."""
        response = self.client.get(reverse('properties:list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Draft Property')

    def test_rejected_property_not_in_public_list(self):
        """REJECTED properties do not appear in public listings."""
        response = self.client.get(reverse('properties:list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Rejected Property')

    def test_rented_property_not_in_public_list(self):
        """RENTED properties do not appear in public listings."""
        response = self.client.get(reverse('properties:list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Rented Property')

    def test_archived_property_not_in_public_list(self):
        """ARCHIVED properties do not appear in public listings."""
        response = self.client.get(reverse('properties:list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Archived Property')

    def test_published_property_in_public_list(self):
        """PUBLISHED properties appear in public listings."""
        response = self.client.get(reverse('properties:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Published Property')

    # =========================================================================
    # TEST 3: Admin can approve property
    # =========================================================================
    def test_admin_can_approve_property(self):
        """Admin can approve a PENDING_REVIEW property."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(
            reverse('dashboard:approve_property', kwargs={'pk': self.pending_property.pk})
        )
        self.pending_property.refresh_from_db()
        self.assertEqual(self.pending_property.status, 'PUBLISHED')

    # =========================================================================
    # TEST 4: Published property is publicly visible
    # =========================================================================
    def test_published_property_visible_publicly(self):
        """PUBLISHED property appears in detail view and list."""
        response = self.client.get(reverse('properties:detail', kwargs={'slug': self.published_property.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Published Property')

    # =========================================================================
    # TEST 5: Rejected property is not public
    # =========================================================================
    def test_rejected_property_not_publicly_accessible(self):
        """REJECTED property cannot be accessed via public detail URL."""
        response = self.client.get(reverse('properties:detail', kwargs={'slug': self.rejected_property.slug}))
        self.assertEqual(response.status_code, 404)

    # =========================================================================
    # TEST 6: Agent cannot edit another agent's property
    # =========================================================================
    def test_agent_cannot_edit_other_agent_property(self):
        """Agent cannot edit a property they don't own."""
        other_agent = User.objects.create_user(
            username='other_agent',
            email='other@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='APPROVED',
            whatsapp_number='2348012345678'
        )
        other_property = Property.objects.create(
            title='Other Agent Property',
            description='Another property with enough description text.',
            price=500000,
            state=self.state,
            lga=self.lga,
            area='Other Area',
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

    # =========================================================================
    # TEST 7: Unauthorized user cannot modify property
    # =========================================================================
    def test_renter_cannot_edit_property(self):
        """Renter cannot edit any property."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.get(reverse('properties:edit', kwargs={'pk': self.published_property.pk}))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_edit_property(self):
        """Anonymous user cannot edit properties."""
        response = self.client.get(reverse('properties:edit', kwargs={'pk': self.published_property.pk}))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    # =========================================================================
    # TEST 8: Images are protected
    # =========================================================================
    def test_only_owner_can_delete_property_image(self):
        """Only property owner can delete images."""
        # Create an image for the published property
        image = PropertyImage.objects.create(
            property=self.published_property,
            image='test_image.jpg',
            is_primary=True,
            order_index=0
        )

        # Another agent tries to delete
        other_agent = User.objects.create_user(
            username='other_agent2',
            email='other2@example.com',
            password='testpass123',
            role='MINOR_ADMIN',
            agent_status='APPROVED',
            whatsapp_number='2348012345678'
        )
        self.client.login(username='other_agent2', password='testpass123')
        response = self.client.post(
            reverse('properties:delete_image', kwargs={'pk': self.published_property.pk, 'image_id': image.pk})
        )
        self.assertEqual(response.status_code, 403)

    # =========================================================================
    # TEST 9: Property status transitions
    # =========================================================================
    def test_draft_can_be_submitted(self):
        """DRAFT property can be submitted for review."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.post(
            reverse('properties:submit', kwargs={'pk': self.draft_property.pk})
        )
        self.draft_property.refresh_from_db()
        self.assertEqual(self.draft_property.status, 'PENDING_REVIEW')

    def test_rejected_can_be_resubmitted(self):
        """REJECTED property can be resubmitted."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.post(
            reverse('properties:resubmit', kwargs={'pk': self.rejected_property.pk})
        )
        self.rejected_property.refresh_from_db()
        self.assertEqual(self.rejected_property.status, 'PENDING_REVIEW')
        self.assertEqual(self.rejected_property.rejection_reason, '')

    def test_published_can_be_marked_rented(self):
        """PUBLISHED property can be marked as RENTED."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.post(
            reverse('properties:rented', kwargs={'pk': self.published_property.pk})
        )
        self.published_property.refresh_from_db()
        self.assertEqual(self.published_property.status, 'RENTED')

    def test_published_can_be_archived(self):
        """PUBLISHED property can be archived."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.post(
            reverse('properties:archive', kwargs={'pk': self.published_property.pk})
        )
        self.published_property.refresh_from_db()
        self.assertEqual(self.published_property.status, 'ARCHIVED')

    def test_rejected_can_be_archived(self):
        """REJECTED property can be archived."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.post(
            reverse('properties:archive', kwargs={'pk': self.rejected_property.pk})
        )
        self.rejected_property.refresh_from_db()
        self.assertEqual(self.rejected_property.status, 'ARCHIVED')

    def test_rented_can_be_archived(self):
        """RENTED property can be archived."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.post(
            reverse('properties:archive', kwargs={'pk': self.rented_property.pk})
        )
        self.rented_property.refresh_from_db()
        self.assertEqual(self.rented_property.status, 'ARCHIVED')

    # =========================================================================
    # TEST 10: Invalid status transitions blocked
    # =========================================================================
    def test_cannot_submit_non_draft(self):
        """Cannot submit a property that is not DRAFT."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.post(
            reverse('properties:submit', kwargs={'pk': self.published_property.pk})
        )
        self.published_property.refresh_from_db()
        self.assertEqual(self.published_property.status, 'PUBLISHED')  # Unchanged

    def test_cannot_resubmit_non_rejected(self):
        """Cannot resubmit a property that is not REJECTED."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.post(
            reverse('properties:resubmit', kwargs={'pk': self.draft_property.pk})
        )
        self.draft_property.refresh_from_db()
        self.assertEqual(self.draft_property.status, 'DRAFT')  # Unchanged

    def test_cannot_mark_non_published_as_rented(self):
        """Cannot mark a non-PUBLISHED property as rented."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.post(
            reverse('properties:rented', kwargs={'pk': self.draft_property.pk})
        )
        self.draft_property.refresh_from_db()
        self.assertEqual(self.draft_property.status, 'DRAFT')  # Unchanged

    def test_cannot_archive_draft(self):
        """DRAFT property cannot be archived."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.post(
            reverse('properties:archive', kwargs={'pk': self.draft_property.pk})
        )
        self.draft_property.refresh_from_db()
        self.assertEqual(self.draft_property.status, 'DRAFT')  # Unchanged

    # =========================================================================
    # TEST 11: Pending agent cannot create property
    # =========================================================================
    def test_pending_agent_cannot_create_property(self):
        """PENDING agent gets 403 when trying to create property."""
        self.client.login(username='pending_agent', password='testpass123')
        response = self.client.get(reverse('properties:create'))
        self.assertEqual(response.status_code, 403)

    def test_rejected_agent_cannot_create_property(self):
        """REJECTED agent gets 403 when trying to create property."""
        self.client.login(username='rejected_agent', password='testpass123')
        response = self.client.get(reverse('properties:create'))
        self.assertEqual(response.status_code, 403)

    def test_suspended_agent_cannot_create_property(self):
        """SUSPENDED agent gets 403 when trying to create property."""
        self.client.login(username='suspended_agent', password='testpass123')
        response = self.client.get(reverse('properties:create'))
        self.assertEqual(response.status_code, 403)

    # =========================================================================
    # TEST 12: Rented property cannot receive new inspection requests
    # =========================================================================
    def test_rented_property_cannot_receive_inspection(self):
        """RENTED property should not allow new inspection requests."""
        # This is enforced at the view level in inspections app
        # Here we verify the property model's is_available method
        self.assertFalse(self.rented_property.is_available())

    def test_archived_property_cannot_receive_inspection(self):
        """ARCHIVED property should not allow new inspection requests."""
        self.assertFalse(self.archived_property.is_available())

    # =========================================================================
    # TEST 13: Property edit restrictions
    # =========================================================================
    def test_rented_property_cannot_be_edited(self):
        """RENTED property cannot be edited by agent."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.get(reverse('properties:edit', kwargs={'pk': self.rented_property.pk}))
        self.assertEqual(response.status_code, 302)  # Redirect with error message

    def test_archived_property_cannot_be_edited(self):
        """ARCHIVED property cannot be edited by agent."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.get(reverse('properties:edit', kwargs={'pk': self.archived_property.pk}))
        self.assertEqual(response.status_code, 302)  # Redirect with error message

    def test_admin_can_edit_any_property(self):
        """Admin can edit any property regardless of status."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('properties:edit', kwargs={'pk': self.rented_property.pk}))
        self.assertEqual(response.status_code, 200)

    # =========================================================================
    # TEST 14: Draft list view
    # =========================================================================
    def test_agent_can_view_drafts(self):
        """Agent can view their draft properties."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.get(reverse('properties:drafts'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Draft Property')

    def test_draft_list_only_shows_drafts(self):
        """Draft list only shows DRAFT properties."""
        self.client.login(username='approved_agent', password='testpass123')
        response = self.client.get(reverse('properties:drafts'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Draft Property')
        self.assertNotContains(response, 'Published Property')
        self.assertNotContains(response, 'Pending Property')


class PropertySearchTests(TestCase):
    """Test property search and filtering."""

    def setUp(self):
        self.client = Client()
        self.state = State.objects.create(name='Lagos', slug='lagos')
        self.lga = LGA.objects.create(state=self.state, name='Lekki', slug='lekki')
        self.state2 = State.objects.create(name='Abuja', slug='abuja')
        self.lga2 = LGA.objects.create(state=self.state2, name='Wuse', slug='wuse')

        # Create published properties
        Property.objects.create(
            title='Lekki Flat',
            description='A flat in Lekki with enough description text.',
            price=1500000,
            state=self.state,
            lga=self.lga,
            area='Lekki Phase 1',
            property_type='3-Bedroom Flat',
            bedrooms=3,
            bathrooms=2,
            agent_name='Agent',
            agent_whatsapp='2348012345678',
            status='PUBLISHED'
        )
        Property.objects.create(
            title='Abuja Duplex',
            description='A duplex in Abuja with enough description text.',
            price=3000000,
            state=self.state2,
            lga=self.lga2,
            area='Wuse 2',
            property_type='4-Bedroom Duplex',
            bedrooms=4,
            bathrooms=3,
            agent_name='Agent',
            agent_whatsapp='2348012345678',
            status='PUBLISHED'
        )
        Property.objects.create(
            title='Budget Flat',
            description='A budget flat with enough description text.',
            price=500000,
            state=self.state,
            lga=self.lga,
            area='Yaba',
            property_type='Mini Flat',
            bedrooms=1,
            bathrooms=1,
            agent_name='Agent',
            agent_whatsapp='2348012345678',
            status='PUBLISHED'
        )

        # Create a non-published property (should not appear in search)
        Property.objects.create(
            title='Hidden Property',
            description='A hidden property with enough description text.',
            price=1000000,
            state=self.state,
            lga=self.lga,
            area='Hidden',
            property_type='3-Bedroom Flat',
            bedrooms=3,
            bathrooms=2,
            agent_name='Agent',
            agent_whatsapp='2348012345678',
            status='PENDING_REVIEW'
        )

    def test_only_published_properties_in_search(self):
        """Only PUBLISHED properties appear in search results."""
        response = self.client.get(reverse('properties:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lekki Flat')
        self.assertContains(response, 'Abuja Duplex')
        self.assertContains(response, 'Budget Flat')
        self.assertNotContains(response, 'Hidden Property')

    def test_filter_by_state(self):
        """Filter properties by state."""
        response = self.client.get(reverse('properties:list'), {'state': self.state.pk})
        self.assertContains(response, 'Lekki Flat')
        self.assertContains(response, 'Budget Flat')
        self.assertNotContains(response, 'Abuja Duplex')

    def test_filter_by_price_range(self):
        """Filter properties by price range."""
        response = self.client.get(reverse('properties:list'), {'min_price': 1000000, 'max_price': 2000000})
        self.assertContains(response, 'Lekki Flat')
        self.assertNotContains(response, 'Abuja Duplex')
        self.assertNotContains(response, 'Budget Flat')

    def test_filter_by_bedrooms(self):
        """Filter properties by minimum bedrooms."""
        response = self.client.get(reverse('properties:list'), {'bedrooms': 3})
        self.assertContains(response, 'Lekki Flat')
        self.assertContains(response, 'Abuja Duplex')
        self.assertNotContains(response, 'Budget Flat')

    def test_filter_by_property_type(self):
        """Filter properties by type."""
        response = self.client.get(reverse('properties:list'), {'property_type': 'Mini Flat'})
        self.assertContains(response, 'Budget Flat')
        self.assertNotContains(response, 'Lekki Flat')
        self.assertNotContains(response, 'Abuja Duplex')

    def test_search_by_keyword(self):
        """Search properties by keyword."""
        response = self.client.get(reverse('properties:list'), {'search': 'Lekki'})
        self.assertContains(response, 'Lekki Flat')
        self.assertNotContains(response, 'Abuja Duplex')

    def test_pagination(self):
        """Search results are paginated."""
        response = self.client.get(reverse('properties:list'))
        self.assertEqual(response.status_code, 200)
        # With 3 published properties and paginate_by=12, all should be on page 1
        self.assertEqual(len(response.context['properties']), 3)
