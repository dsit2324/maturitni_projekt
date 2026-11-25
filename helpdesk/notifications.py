from django.conf import settings
from django.core.mail import send_mail

from .models import Notification, User


def notify_user(recipient, ticket, message, *, actor=None):
    if not recipient.is_active or recipient == actor:
        return

    Notification.objects.create(recipient=recipient, ticket=ticket, message=message)
    if recipient.email:
        send_mail(
            subject=f'Helpdesk: {ticket.title}',
            message=(
                f'{message}\n\nOtevřít požadavek: '
                f'{settings.SITE_URL.rstrip("/")}/tickets/{ticket.pk}/'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            fail_silently=False,
        )


def notify_technicians(ticket, message, *, actor=None):
    technicians = User.objects.filter(
        role=User.ROLE_TECHNICIAN,
        is_active=True,
    )

    if ticket.category_id:
        specialists = technicians.filter(specialties=ticket.category)
        if specialists.exists():
            technicians = specialists
        else:
            generalists = technicians.filter(specialties__isnull=True)
            if generalists.exists():
                technicians = generalists
            else:
                technicians = technicians.none()

    recipients = technicians | User.objects.filter(
        role=User.ROLE_ADMIN,
        is_active=True,
    )
    for technician in recipients.distinct():
        notify_user(technician, ticket, message, actor=actor)
