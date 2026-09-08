from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from properties.models import Property, State, LGA
from favourites.models import Favourite

User = get_user_model()


class FavouriteTests(TestCase):
    def setUp(self):
        self.client = Client()
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
            status='PUBLISHED'
        )

    def test_renter_can_favourite(self):
        """Authenticated renter can favourite a property."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('favourites:toggle', kwargs={'property_id': self.property.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Favourite.objects.filter(user=self.renter, property=self.property).exists())

    def test_duplicate_favourite_prevented(self):
        """Database prevents duplicate favourites."""
        Favourite.objects.create(user=self.renter, property=self.property)
        with self.assertRaises(IntegrityError):
            Favourite.objects.create(user=self.renter, property=self.property)

    def test_renter_can_unfavourite(self):
        """Renter can remove a favourite."""
        Favourite.objects.create(user=self.renter, property=self.property)
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('favourites:toggle', kwargs={'property_id': self.property.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Favourite.objects.filter(user=self.renter, property=self.property).exists())

    def test_renter_can_view_favourites(self):
        """Renter can view their favourites list."""
        Favourite.objects.create(user=self.renter, property=self.property)
        self.client.login(username='renter', password='testpass123')
        response = self.client.get(reverse('favourites:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Property')

    def test_anonymous_cannot_favourite(self):
        """Anonymous user cannot favourite."""
        response = self.client.post(
            reverse('favourites:toggle', kwargs={'property_id': self.property.pk})
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_user_cannot_see_other_favourites(self):
        """User cannot see another user's favourites."""
        Favourite.objects.create(user=self.other_renter, property=self.property)
        self.client.login(username='renter', password='testpass123')
        response = self.client.get(reverse('favourites:list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Test Property')

    def test_ajax_toggle_returns_json_and_persists(self):
        """The fetch()-based toggle (see static/js/app.js initFavouriteToggle)
        must actually persist the favourite, not just report success - this
        guards against the fake-toggle regression the original JS had, where
        the icon flipped client-side but nothing was ever saved."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('favourites:toggle', kwargs={'property_id': self.property.pk}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['favourited'])
        self.assertEqual(data['favourite_count'], 1)
        self.assertTrue(Favourite.objects.filter(user=self.renter, property=self.property).exists())

        # Toggling again via AJAX removes it
        response = self.client.post(
            reverse('favourites:toggle', kwargs={'property_id': self.property.pk}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        data = response.json()
        self.assertFalse(data['favourited'])
        self.assertEqual(data['favourite_count'], 0)
        self.assertFalse(Favourite.objects.filter(user=self.renter, property=self.property).exists())

    def test_non_ajax_toggle_still_redirects(self):
        """A plain <form> submit (no X-Requested-With header) still gets the
        original redirect-based behaviour, so browsers with JS disabled (or
        the fetch() fallback path in app.js) keep working."""
        self.client.login(username='renter', password='testpass123')
        response = self.client.post(
            reverse('favourites:toggle', kwargs={'property_id': self.property.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Favourite.objects.filter(user=self.renter, property=self.property).exists())
