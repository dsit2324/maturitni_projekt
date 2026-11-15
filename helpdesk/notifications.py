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
    for technician in User.objects.filter(
        role__in=(User.ROLE_TECHNICIAN, User.ROLE_ADMIN),
        is_active=True,
    ):
        notify_user(technician, ticket, message, actor=actor)
