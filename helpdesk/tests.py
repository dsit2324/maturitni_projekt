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
