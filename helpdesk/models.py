from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class HelpdeskUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    ROLE_USER = 'user'
    ROLE_TECHNICIAN = 'technician'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_USER, 'Uživatel'),
        (ROLE_TECHNICIAN, 'Technik'),
        (ROLE_ADMIN, 'Administrátor'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)

    objects = HelpdeskUserManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=['user', 'technician', 'admin']),
                name='helpdesk_user_role_valid',
            ),
        ]

    def clean(self):
        super().clean()
        if (
            self.pk
            and self.role != self.ROLE_TECHNICIAN
            and Ticket.objects.filter(assignee_id=self.pk).exists()
        ):
            raise ValidationError({'role': 'Před změnou role je nutné přeřadit přiřazené požadavky.'})

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Ticket(models.Model):
    STATUS_NEW = 'new'
    STATUS_ACCEPTED = 'accepted'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_PENDING = 'pending'
    STATUS_RESOLVED = 'resolved'
    STATUS_CLOSED = 'closed'

    STATUS_CHOICES = [
        (STATUS_NEW, 'Nový'),
        (STATUS_ACCEPTED, 'Přijatý'),
        (STATUS_IN_PROGRESS, 'Řeší se'),
        (STATUS_PENDING, 'Čeká se'),
        (STATUS_RESOLVED, 'Vyřešený'),
        (STATUS_CLOSED, 'Uzavřený'),
    ]

    PRIORITY_LOW = 'low'
    PRIORITY_NORMAL = 'normal'
    PRIORITY_HIGH = 'high'
    PRIORITY_CRITICAL = 'critical'

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Nízká'),
        (PRIORITY_NORMAL, 'Normální'),
        (PRIORITY_HIGH, 'Vysoká'),
        (PRIORITY_CRITICAL, 'Kritická'),
    ]

    STATUS_TRANSITIONS = {
        STATUS_NEW: {STATUS_ACCEPTED},
        STATUS_ACCEPTED: {STATUS_IN_PROGRESS, STATUS_PENDING},
        STATUS_IN_PROGRESS: {STATUS_PENDING, STATUS_RESOLVED},
        STATUS_PENDING: {STATUS_IN_PROGRESS},
        STATUS_RESOLVED: {STATUS_CLOSED, STATUS_IN_PROGRESS},
        STATUS_CLOSED: {STATUS_IN_PROGRESS},
    }

    title = models.CharField(max_length=200)
    description = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='tickets',
        db_index=False,
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        db_index=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_tickets',
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['author', '-created_at'], name='ticket_author_created_idx'),
            models.Index(fields=['assignee', 'status'], name='ticket_assignee_status_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=['new', 'accepted', 'in_progress', 'pending', 'resolved', 'closed']),
                name='helpdesk_ticket_status_valid',
            ),
            models.CheckConstraint(
                condition=models.Q(priority__in=['low', 'normal', 'high', 'critical']),
                name='helpdesk_ticket_priority_valid',
            ),
            models.CheckConstraint(
                condition=models.Q(resolved_at__isnull=True)
                | models.Q(resolved_at__gte=models.F('created_at')),
                name='helpdesk_ticket_resolved_at_valid',
            ),
        ]

    def __str__(self):
        return self.title

    def validate_status_transition(self, new_status=None):
        requested_status = new_status or self.status
        if self._state.adding or not self.pk:
            if requested_status != self.STATUS_NEW:
                raise ValidationError({'status': 'Nový požadavek musí začínat ve stavu Nový.'})
            return

        previous_status = Ticket.objects.filter(pk=self.pk).values_list('status', flat=True).first()
        if previous_status is None or previous_status == requested_status:
            return
        if requested_status not in self.STATUS_TRANSITIONS.get(previous_status, set()):
            raise ValidationError({'status': 'Tento přechod stavu není povolen.'})

    def clean(self):
        super().clean()
        self.validate_status_transition()

        if self.assignee_id and not User.objects.filter(
            pk=self.assignee_id,
            role=User.ROLE_TECHNICIAN,
        ).exists():
            raise ValidationError({'assignee': 'Požadavek lze přiřadit pouze technikovi.'})

        if self.resolved_at and self.created_at and self.resolved_at < self.created_at:
            raise ValidationError({'resolved_at': 'Čas vyřešení nesmí předcházet vytvoření požadavku.'})

        if self.status not in {self.STATUS_RESOLVED, self.STATUS_CLOSED} and self.resolved_at:
            raise ValidationError({'resolved_at': 'Čas vyřešení je povolen pouze u vyřešeného nebo uzavřeného požadavku.'})

    @transaction.atomic
    def save(self, *args, **kwargs):
        previous = Ticket.objects.filter(pk=self.pk).first() if self.pk else None
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_fields = set(update_fields)
            if 'status' in update_fields:
                update_fields.add('resolved_at')
            kwargs['update_fields'] = update_fields

        if self.status == self.STATUS_RESOLVED:
            if previous is None or previous.status != self.STATUS_RESOLVED or self.resolved_at is None:
                self.resolved_at = timezone.now()
        elif self.status == self.STATUS_CLOSED and previous is not None:
            self.resolved_at = previous.resolved_at
        elif (
            self.status == self.STATUS_IN_PROGRESS
            and previous is not None
            and previous.status in {self.STATUS_RESOLVED, self.STATUS_CLOSED}
        ):
            self.resolved_at = None
        else:
            self.resolved_at = None

        self.clean()
        super().save(*args, **kwargs)

        if previous is None:
            return

        history_fields = (
            'title',
            'description',
            'status',
            'priority',
            'assignee',
            'category',
            'resolved_at',
        )
        for field_name in history_fields:
            if (
                update_fields is not None
                and field_name not in update_fields
                and f'{field_name}_id' not in update_fields
            ):
                continue

            if field_name in {'assignee', 'category'}:
                old_value = getattr(previous, f'{field_name}_id')
                new_value = getattr(self, f'{field_name}_id')
            else:
                old_value = getattr(previous, field_name)
                new_value = getattr(self, field_name)

            if old_value != new_value:
                TicketHistory.objects.create(
                    ticket=self,
                    changed_by=self.updated_by,
                    field_name=field_name,
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(new_value) if new_value is not None else None,
                )


class Comment(models.Model):
    ticket = models.ForeignKey(
        'Ticket',
        on_delete=models.CASCADE,
        related_name='comments',
        db_index=False,
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['ticket', 'created_at'], name='comment_ticket_created_idx'),
        ]

    def __str__(self):
        return f'{self.author} -> {self.ticket}'


class TicketSolution(models.Model):
    ticket = models.OneToOneField('Ticket', on_delete=models.CASCADE, related_name='solution')
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='solutions')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Řešení: {self.ticket}'


class TicketHistory(models.Model):
    ticket = models.ForeignKey(
        'Ticket',
        on_delete=models.CASCADE,
        related_name='history',
        db_index=False,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='ticket_changes',
    )
    field_name = models.CharField(max_length=50)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket', '-created_at'], name='history_ticket_created_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    field_name__in=[
                        'title',
                        'description',
                        'status',
                        'priority',
                        'assignee',
                        'updated_by',
                        'category',
                        'resolved_at',
                    ]
                ),
                name='helpdesk_tickethistory_field_name_valid',
            ),
        ]

    def __str__(self):
        return f'{self.ticket} / {self.field_name}'
