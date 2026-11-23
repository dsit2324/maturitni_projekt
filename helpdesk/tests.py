import tempfile
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    Category,
    Comment,
    KnowledgeArticle,
    Notification,
    Ticket,
    TicketAttachment,
    TicketFeedback,
    TicketHistory,
    User,
)


class HelpdeskModelTests(TestCase):
    def test_user_role_default_is_user(self):
        user = User.objects.create_user(username='testuser', password='heslo123')
        self.assertEqual(user.role, User.ROLE_USER)

    def test_application_role_is_independent_from_django_staff_flags(self):
        admin = User.objects.create_user(username='appadmin', password='heslo123', role=User.ROLE_ADMIN)
        self.assertFalse(admin.is_staff)

        django_staff = User.objects.create_user(
            username='django-staff',
            password='heslo123',
            role=User.ROLE_USER,
            is_staff=True,
        )
        self.assertEqual(django_staff.role, User.ROLE_USER)

        superuser = User.objects.create_superuser(username='superadmin', password='heslo123')
        self.assertEqual(superuser.role, User.ROLE_ADMIN)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

    def test_password_is_hashed_when_saved_directly(self):
        user = User(username='raw_password_user', password='heslo123')
        user.save()

        self.assertNotEqual(user.password, 'heslo123')
        self.assertTrue(user.check_password('heslo123'))

    def test_ticket_creation_requires_title_and_description(self):
        category, _ = Category.objects.get_or_create(
            name='Hardware', defaults={'description': 'Počítače a periferie'}
        )
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
        category, _ = Category.objects.get_or_create(
            name='Hardware', defaults={'description': 'Počítače a periferie'}
        )
        user = User.objects.create_user(username='autor', password='heslo123')
        ticket = Ticket.objects.create(
            title='Nefunguje klávesnice',
            description='Po zapnutí počítače nefunguje klávesnice.',
            author=user,
            category=category,
        )

        ticket.status = Ticket.STATUS_ACCEPTED
        ticket.updated_by = user
        ticket.save()

        history_entry = TicketHistory.objects.filter(ticket=ticket, field_name='status').first()
        self.assertIsNotNone(history_entry)
        self.assertEqual(history_entry.old_value, Ticket.STATUS_NEW)
        self.assertEqual(history_entry.new_value, Ticket.STATUS_ACCEPTED)

    def test_ticket_status_transitions_and_reopening_are_enforced(self):
        author = User.objects.create_user(username='autor', password='heslo123')
        ticket = Ticket.objects.create(
            title='Testovací požadavek',
            description='Popis požadavku',
            author=author,
        )

        ticket.status = Ticket.STATUS_CLOSED
        with self.assertRaises(ValidationError):
            ticket.save()

        ticket.status = Ticket.STATUS_ACCEPTED
        ticket.save()
        ticket.status = Ticket.STATUS_IN_PROGRESS
        ticket.save()
        ticket.status = Ticket.STATUS_RESOLVED
        ticket.save(update_fields=['status'])
        ticket.refresh_from_db()
        resolved_at = ticket.resolved_at
        self.assertIsNotNone(resolved_at)

        ticket.status = Ticket.STATUS_CLOSED
        ticket.save()
        self.assertEqual(ticket.resolved_at, resolved_at)
        ticket.status = Ticket.STATUS_IN_PROGRESS
        ticket.save()

        self.assertIsNone(ticket.resolved_at)
        self.assertEqual(
            TicketHistory.objects.filter(ticket=ticket, field_name='status').count(),
            5,
        )
        self.assertTrue(
            TicketHistory.objects.filter(ticket=ticket, field_name='resolved_at').exists()
        )

    def test_ticket_must_be_assigned_to_a_technician_or_admin(self):
        author = User.objects.create_user(username='autor', password='heslo123')
        ordinary_user = User.objects.create_user(username='bezrole', password='heslo123')

        with self.assertRaises(ValidationError):
            Ticket.objects.create(
                title='Testovací požadavek',
                description='Popis požadavku',
                author=author,
                assignee=ordinary_user,
            )

    def test_ticket_can_be_assigned_to_admin_but_not_inactive_technician(self):
        author = User.objects.create_user(username='autor', password='heslo123')
        admin = User.objects.create_user(
            username='administrator',
            password='heslo123',
            role=User.ROLE_ADMIN,
        )
        ticket = Ticket.objects.create(
            title='Testovací požadavek',
            description='Popis požadavku',
            author=author,
            assignee=admin,
        )
        self.assertEqual(ticket.assignee, admin)

        admin.is_active = False
        admin.save(update_fields=['is_active'])
        with self.assertRaises(ValidationError):
            ticket.assignee = admin
            ticket.save()

    def test_assigned_technician_cannot_be_demoted_before_reassignment(self):
        author = User.objects.create_user(username='autor', password='heslo123')
        technician = User.objects.create_user(
            username='technik',
            password='heslo123',
            role=User.ROLE_TECHNICIAN,
        )
        Ticket.objects.create(
            title='Testovací požadavek',
            description='Popis požadavku',
            author=author,
            assignee=technician,
        )

        technician.role = User.ROLE_USER
        with self.assertRaises(ValidationError):
            technician.save()

        technician.refresh_from_db()
        self.assertEqual(technician.role, User.ROLE_TECHNICIAN)

    def test_user_with_ticket_cannot_be_deleted(self):
        author = User.objects.create_user(username='autor', password='heslo123')
        ticket = Ticket.objects.create(
            title='Testovací požadavek',
            description='Popis požadavku',
            author=author,
        )

        with self.assertRaises(ProtectedError):
            author.delete()

        self.assertTrue(User.objects.filter(pk=author.pk).exists())
        self.assertTrue(Ticket.objects.filter(pk=ticket.pk).exists())

    def test_user_with_audit_history_cannot_be_deleted(self):
        author = User.objects.create_user(username='autor', password='heslo123')
        technician = User.objects.create_user(
            username='technik',
            password='heslo123',
            role=User.ROLE_TECHNICIAN,
        )
        ticket = Ticket.objects.create(
            title='Testovací požadavek',
            description='Popis požadavku',
            author=author,
            updated_by=technician,
        )
        ticket.status = Ticket.STATUS_ACCEPTED
        ticket.save()

        with self.assertRaises(ProtectedError):
            technician.delete()

        self.assertTrue(TicketHistory.objects.filter(ticket=ticket, changed_by=technician).exists())

    def test_invalid_user_role_is_rejected_by_database(self):
        with self.assertRaises(IntegrityError):
            User.objects.bulk_create(
                [User(username='badrole', password='password123', role='unknown-role')]
            )

    def test_invalid_ticket_status_and_priority_are_rejected_by_database(self):
        user = User.objects.create_user(username='autor', password='heslo123')
        category, _ = Category.objects.get_or_create(
            name='Hardware', defaults={'description': 'Počítače a periferie'}
        )

        with self.assertRaises(IntegrityError):
            Ticket.objects.bulk_create(
                [
                    Ticket(
                        title='Neplatný stav',
                        description='Test neplatné hodnoty.',
                        author=user,
                        category=category,
                        status='invalid-status',
                        priority='invalid-priority',
                    )
                ]
            )

    def test_dashboard_counts_pending_and_closed_tickets(self):
        user = User.objects.create_user(username='adminuser', password='heslo123', role=User.ROLE_ADMIN)
        pending_ticket = Ticket.objects.create(title='Pauza 1', description='Čekající požadavek', author=user)
        pending_ticket.status = Ticket.STATUS_ACCEPTED
        pending_ticket.save()
        pending_ticket.status = Ticket.STATUS_IN_PROGRESS
        pending_ticket.save()
        pending_ticket.status = Ticket.STATUS_PENDING
        pending_ticket.save()

        closed_ticket = Ticket.objects.create(title='Pauza 2', description='Uzavřený požadavek', author=user)
        closed_ticket.status = Ticket.STATUS_ACCEPTED
        closed_ticket.save()
        closed_ticket.status = Ticket.STATUS_IN_PROGRESS
        closed_ticket.save()
        closed_ticket.status = Ticket.STATUS_RESOLVED
        closed_ticket.save()
        closed_ticket.status = Ticket.STATUS_CLOSED
        closed_ticket.save()

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

    def test_login_redirects_to_safe_next_url_and_ignores_external_urls(self):
        response = self.client.post(
            f"{reverse('login')}?next={reverse('ticket_list')}",
            {'username': self.user.username, 'password': 'heslo123', 'next': reverse('ticket_list')},
        )
        self.assertRedirects(response, reverse('ticket_list'))

        self.client.logout()
        response = self.client.post(
            reverse('login'),
            {'username': self.user.username, 'password': 'heslo123', 'next': 'https://example.com'},
        )
        self.assertRedirects(response, reverse('dashboard'))

    def test_logout_requires_post(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

    def test_invalid_comment_error_is_visible(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('ticket_detail', args=[self.ticket.pk]),
            {'comment_submit': '1', 'content': ''},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'form-error')
        self.assertTrue(response.context['comment_form'].has_error('content'))

    def test_invalid_status_transition_error_is_visible(self):
        self.client.force_login(self.technician)

        response = self.client.post(
            reverse('ticket_detail', args=[self.ticket.pk]),
            {'status_submit': '1', 'status': Ticket.STATUS_CLOSED, 'priority': Ticket.PRIORITY_NORMAL},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tento přechod stavu není povolen.')

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

    def test_regular_user_cannot_choose_ticket_priority_in_web_form(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('create_ticket'),
            {
                'title': 'Požadavek s nepovolenou prioritou',
                'description': 'Prioritu určuje helpdesk.',
                'priority': Ticket.PRIORITY_CRITICAL,
            },
        )

        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(title='Požadavek s nepovolenou prioritou')
        self.assertEqual(ticket.priority, Ticket.PRIORITY_NORMAL)

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
            {'status_submit': '1', 'status': Ticket.STATUS_ACCEPTED, 'priority': Ticket.PRIORITY_NORMAL},
        )

        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.STATUS_ACCEPTED)

    def test_api_rejects_invalid_ticket_status_transition(self):
        self.client.force_login(self.technician)
        response = self.client.patch(
            reverse('api_ticket_detail', args=[self.ticket.pk]),
            {'status': Ticket.STATUS_CLOSED},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.STATUS_NEW)

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

    def test_internal_comments_are_hidden_from_users_and_user_cannot_create_them(self):
        Comment.objects.create(
            ticket=self.ticket,
            author=self.technician,
            content='Interní informace',
            is_internal=True,
        )
        self.client.force_login(self.technician)
        self.client.post(
            reverse('ticket_detail', args=[self.ticket.pk]),
            {
                'comment_submit': '1',
                'content': 'Interní poznámka přes formulář',
                'is_internal': 'on',
            },
        )
        self.assertTrue(
            Comment.objects.get(content='Interní poznámka přes formulář').is_internal
        )
        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.first_response_at)
        self.client.post(
            reverse('ticket_detail', args=[self.ticket.pk]),
            {'comment_submit': '1', 'content': 'Veřejná odpověď technika'},
        )
        self.ticket.refresh_from_db()
        self.assertIsNotNone(self.ticket.first_response_at)

        self.client.force_login(self.user)
        response = self.client.get(reverse('ticket_detail', args=[self.ticket.pk]))
        self.assertNotContains(response, 'Interní informace')
        self.assertNotContains(response, 'Interní poznámka přes formulář')
        self.client.post(
            reverse('ticket_detail', args=[self.ticket.pk]),
            {'comment_submit': '1', 'content': 'Pokus o skrytý komentář', 'is_internal': 'on'},
        )
        user_comment = Comment.objects.get(content='Pokus o skrytý komentář')
        self.assertFalse(user_comment.is_internal)

        self.client.force_login(self.technician)
        response = self.client.get(reverse('ticket_detail', args=[self.ticket.pk]))
        self.assertContains(response, 'Interní informace')

    def test_ticket_sla_deadlines_follow_priority(self):
        self.ticket.priority = Ticket.PRIORITY_HIGH
        self.ticket.save()

        self.assertEqual(
            self.ticket.resolution_due_at - self.ticket.first_response_due_at,
            timedelta(hours=20),
        )

    def test_ticket_search_supports_ticket_number_and_pagination(self):
        for index in range(21):
            Ticket.objects.create(
                title=f'Další požadavek {index}',
                description='Testovací popis',
                author=self.user,
            )
        self.client.force_login(self.user)

        second_page = self.client.get(reverse('ticket_list'), {'page': 2})
        self.assertEqual(len(second_page.context['tickets']), 2)

        by_number = self.client.get(reverse('ticket_list'), {'q': str(self.ticket.pk)})
        self.assertEqual(list(by_number.context['tickets']), [self.ticket])

    def test_attachment_upload_and_download_are_ticket_authorized(self):
        with tempfile.TemporaryDirectory() as media_dir, override_settings(MEDIA_ROOT=media_dir):
            self.client.force_login(self.user)
            response = self.client.post(
                reverse('ticket_detail', args=[self.ticket.pk]),
                {
                    'attachment_submit': '1',
                    'file': SimpleUploadedFile('error.txt', b'error details', content_type='text/plain'),
                },
            )
            self.assertEqual(response.status_code, 302)
            attachment = TicketAttachment.objects.get(ticket=self.ticket)

            download = self.client.get(reverse('attachment_download', args=[attachment.pk]))
            self.assertEqual(download.status_code, 200)
            self.assertIn('error.txt', download['Content-Disposition'])

            other_user = User.objects.create_user(username='jiny', password='heslo123')
            self.client.force_login(other_user)
            denied = self.client.get(reverse('attachment_download', args=[attachment.pk]))
            self.assertEqual(denied.status_code, 404)

            self.client.force_login(self.user)
            invalid_upload = self.client.post(
                reverse('ticket_detail', args=[self.ticket.pk]),
                {
                    'attachment_submit': '1',
                    'file': SimpleUploadedFile('malware.exe', b'not executable', content_type='application/octet-stream'),
                },
            )
            self.assertEqual(invalid_upload.status_code, 200)
            self.assertEqual(TicketAttachment.objects.filter(ticket=self.ticket).count(), 1)

    def test_feedback_requires_resolved_ticket_and_is_stored(self):
        self.ticket.status = Ticket.STATUS_ACCEPTED
        self.ticket.save()
        self.ticket.status = Ticket.STATUS_IN_PROGRESS
        self.ticket.save()
        self.ticket.status = Ticket.STATUS_RESOLVED
        self.ticket.save()
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('ticket_detail', args=[self.ticket.pk]),
            {'feedback_submit': '1', 'rating': '5', 'comment': 'Rychlé vyřešení'},
        )
        self.assertEqual(response.status_code, 302)
        feedback = TicketFeedback.objects.get(ticket=self.ticket)
        self.assertEqual(feedback.rating, 5)
        self.assertEqual(feedback.comment, 'Rychlé vyřešení')

    def test_knowledge_base_only_lists_published_articles_for_users(self):
        published = KnowledgeArticle.objects.create(
            title='Reset hesla',
            slug='reset-hesla',
            content='Postup resetu.',
            created_by=self.admin,
            is_published=True,
        )
        unpublished = KnowledgeArticle.objects.create(
            title='Interní návod',
            slug='interni-navod',
            content='Pouze pro techniky.',
            created_by=self.admin,
        )
        self.client.force_login(self.user)

        listing = self.client.get(reverse('knowledge_base'))
        self.assertContains(listing, published.title)
        self.assertNotContains(listing, unpublished.title)
        self.assertEqual(
            self.client.get(
                reverse('knowledge_article_detail', args=[unpublished.slug])
            ).status_code,
            404,
        )

    def test_ticket_status_change_creates_an_in_app_notification(self):
        self.client.force_login(self.technician)
        self.user.email = 'user@example.com'
        self.user.save(update_fields=['email'])
        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(
                reverse('ticket_detail', args=[self.ticket.pk]),
                {'status_submit': '1', 'status': Ticket.STATUS_ACCEPTED, 'priority': Ticket.PRIORITY_NORMAL},
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.user,
                ticket=self.ticket,
                message__contains='Přijatý',
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
