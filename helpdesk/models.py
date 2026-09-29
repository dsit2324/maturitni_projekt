from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


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
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username


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

    title = models.CharField(max_length=200)
    description = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tickets')
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
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

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.pk:
            previous = Ticket.objects.filter(pk=self.pk).first()
            if previous is not None:
                for field_name in ['status', 'priority', 'assignee', 'updated_by']:
                    old_value = getattr(previous, field_name)
                    new_value = getattr(self, field_name)

                    if field_name == 'assignee' and old_value is not None:
                        old_value = old_value.pk
                    if field_name == 'updated_by' and old_value is not None:
                        old_value = old_value.pk
                    if field_name == 'assignee' and new_value is not None:
                        new_value = new_value.pk
                    if field_name == 'updated_by' and new_value is not None:
                        new_value = new_value.pk

                    if old_value != new_value:
                        TicketHistory.objects.create(
                            ticket=self,
                            changed_by=self.updated_by,
                            field_name=field_name,
                            old_value=str(old_value) if old_value is not None else None,
                            new_value=str(new_value) if new_value is not None else None,
                        )

        super().save(*args, **kwargs)


class Comment(models.Model):
    ticket = models.ForeignKey('Ticket', on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author} -> {self.ticket}'


class TicketSolution(models.Model):
    ticket = models.OneToOneField('Ticket', on_delete=models.CASCADE, related_name='solution')
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='solutions')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Řešení: {self.ticket}'


class TicketHistory(models.Model):
    ticket = models.ForeignKey('Ticket', on_delete=models.CASCADE, related_name='history')
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
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

    def __str__(self):
        return f'{self.ticket} / {self.field_name}'
