from django.test import TestCase

from .models import Category, Ticket, User


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
