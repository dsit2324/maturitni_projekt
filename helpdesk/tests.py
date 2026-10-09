from django.test import TestCase
from django.urls import reverse

from .models import Category, Ticket, TicketHistory, User


class HelpdeskModelTests(TestCase):
    def test_user_role_default_is_user(self):
        user = User.objects.create_user(username='testuser', password='heslo123')
        self.assertEqual(user.role, User.ROLE_USER)

    def test_ticket_creation_requires_title_and_description(self):
        category = Category.objects.create(name='Hardware', description='Počítače a periferie')
        user = User.objects.create_user(username='autor', password='heslo123')

        ticket = Ticket.objects.create(
            title='Nefunguje klávesnice',
            description='Po zapnutí počítače nefunguje klávesnice.',
            author=user,
            category=category,
        )

        self.assertEqual(ticket.title, 'Nefunguje klávesnice')
        self.assertEqual(ticket.status, Ticket.STATUS_NEW)

    def test_ticket_history_is_created_when_status_changes(self):
        category = Category.objects.create(name='Hardware', description='Počítače a periferie')
        user = User.objects.create_user(username='autor', password='heslo123')
        ticket = Ticket.objects.create(
            title='Nefunguje klávesnice',
            description='Po zapnutí počítače nefunguje klávesnice.',
            author=user,
            category=category,
        )

        ticket.status = Ticket.STATUS_IN_PROGRESS
        ticket.updated_by = user
        ticket.save()

        history_entry = TicketHistory.objects.filter(ticket=ticket, field_name='status').first()
        self.assertIsNotNone(history_entry)
        self.assertEqual(history_entry.old_value, Ticket.STATUS_NEW)
        self.assertEqual(history_entry.new_value, Ticket.STATUS_IN_PROGRESS)

    def test_dashboard_counts_pending_and_closed_tickets(self):
        user = User.objects.create_user(username='adminuser', password='heslo123', role=User.ROLE_ADMIN)
        Category.objects.create(name='Hardware', description='Počítače a periferie')

        Ticket.objects.create(
            title='Pauza 1',
            description='Čekající požadavek',
            author=user,
            status=Ticket.STATUS_PENDING,
        )
        Ticket.objects.create(
            title='Pauza 2',
            description='Uzavřený požadavek',
            author=user,
            status=Ticket.STATUS_CLOSED,
        )

        self.client.force_login(user)
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.context['pending_tickets'], 1)
        self.assertEqual(response.context['closed_tickets'], 1)


class RoleAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='uzivatel', password='heslo123')
        self.technician = User.objects.create_user(
            username='technik', password='heslo123', role=User.ROLE_TECHNICIAN
        )
        self.admin = User.objects.create_user(username='admin', password='heslo123', role=User.ROLE_ADMIN)
        self.ticket = Ticket.objects.create(
            title='Testovací požadavek',
            description='Popis požadavku',
            author=self.user,
        )

    def test_registration_does_not_allow_selecting_a_role(self):
        self.client.post(
            reverse('register'),
            {
                'username': 'novy',
                'email': 'novy@example.com',
                'password1': 'bezpecne-heslo-9876',
                'password2': 'bezpecne-heslo-9876',
                'role': User.ROLE_ADMIN,
            },
        )

        registered_user = User.objects.get(username='novy')
        self.assertEqual(registered_user.role, User.ROLE_USER)
        self.assertFalse(registered_user.is_staff)

    def test_regular_user_cannot_set_managed_fields_when_creating_ticket_via_api(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('api_tickets'),
            {
                'title': 'Nový požadavek',
                'description': 'Popis požadavku',
                'status': Ticket.STATUS_CLOSED,
                'priority': Ticket.PRIORITY_CRITICAL,
                'assignee_id': self.technician.pk,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        created_ticket = Ticket.objects.get(title='Nový požadavek')
        self.assertEqual(created_ticket.author, self.user)
        self.assertEqual(created_ticket.status, Ticket.STATUS_NEW)
        self.assertEqual(created_ticket.priority, Ticket.PRIORITY_NORMAL)
        self.assertIsNone(created_ticket.assignee)

    def test_only_technician_or_admin_can_change_ticket_status(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('ticket_detail', args=[self.ticket.pk]),
            {'status_submit': '1', 'status': Ticket.STATUS_CLOSED, 'priority': Ticket.PRIORITY_CRITICAL},
        )

        self.assertEqual(response.status_code, 403)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.STATUS_NEW)

        self.client.force_login(self.technician)
        response = self.client.post(
            reverse('ticket_detail', args=[self.ticket.pk]),
            {'status_submit': '1', 'status': Ticket.STATUS_IN_PROGRESS, 'priority': Ticket.PRIORITY_NORMAL},
        )

        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.STATUS_IN_PROGRESS)

    def test_api_users_cannot_update_or_delete_tickets(self):
        self.client.force_login(self.user)
        detail_url = reverse('api_ticket_detail', args=[self.ticket.pk])

        update_response = self.client.patch(detail_url, {'status': Ticket.STATUS_CLOSED}, content_type='application/json')
        delete_response = self.client.delete(detail_url)

        self.assertEqual(update_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        self.assertTrue(Ticket.objects.filter(pk=self.ticket.pk).exists())

    def test_only_admin_can_delete_tickets_through_api(self):
        detail_url = reverse('api_ticket_detail', args=[self.ticket.pk])

        self.client.force_login(self.technician)
        self.assertEqual(self.client.delete(detail_url).status_code, 403)

        self.client.force_login(self.admin)
        self.assertEqual(self.client.delete(detail_url).status_code, 204)
        self.assertFalse(Ticket.objects.filter(pk=self.ticket.pk).exists())
