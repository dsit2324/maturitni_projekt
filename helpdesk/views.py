from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, When
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .forms import (
    CommentForm,
    RegisterForm,
    TicketAttachmentForm,
    TicketFeedbackForm,
    TicketForm,
    TicketStatusForm,
)
from .models import (
    Category,
    Comment,
    KnowledgeArticle,
    Notification,
    Ticket,
    TicketAttachment,
    TicketFeedback,
    User,
)
from .notifications import notify_technicians, notify_user
from .serializers import TicketSerializer


def priority_ordered(queryset):
    return queryset.annotate(
        priority_rank=Case(
            When(priority=Ticket.PRIORITY_CRITICAL, then=1),
            When(priority=Ticket.PRIORITY_HIGH, then=2),
            When(priority=Ticket.PRIORITY_NORMAL, then=3),
            When(priority=Ticket.PRIORITY_LOW, then=4),
            default=5,
            output_field=IntegerField(),
        )
    ).order_by('priority_rank', '-created_at')


@login_required
def dashboard(request):
    queryset = Ticket.objects.select_related('author', 'assignee', 'category')
    if request.user.role == User.ROLE_USER:
        queryset = queryset.filter(author=request.user)

    total = queryset.count()
    new = queryset.filter(status=Ticket.STATUS_NEW).count()
    accepted = queryset.filter(status=Ticket.STATUS_ACCEPTED).count()
    in_progress = queryset.filter(status=Ticket.STATUS_IN_PROGRESS).count()
    pending = queryset.filter(status=Ticket.STATUS_PENDING).count()
    resolved = queryset.filter(status=Ticket.STATUS_RESOLVED).count()
    closed = queryset.filter(status=Ticket.STATUS_CLOSED).count()
    critical = queryset.filter(priority=Ticket.PRIORITY_CRITICAL).count()
    recent = priority_ordered(queryset)[:5]
    now = timezone.now()
    overdue = queryset.exclude(
        status__in=(Ticket.STATUS_RESOLVED, Ticket.STATUS_CLOSED)
    ).filter(
        Q(first_response_due_at__lt=now, first_response_at__isnull=True)
        | Q(resolution_due_at__lt=now)
    ).count()

    context = {
        'total_tickets': total,
        'new_tickets': new,
        'accepted_tickets': accepted,
        'in_progress_tickets': in_progress,
        'pending_tickets': pending,
        'resolved_tickets': resolved,
        'closed_tickets': closed,
        'critical_tickets': critical,
        'overdue_tickets': overdue,
        'recent_tickets': recent,
    }
    return render(request, 'dashboard.html', context)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registrace byla úspěšná.')
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('dashboard')
        messages.error(request, 'Neplatné přihlašovací údaje.')
    else:
        next_url = request.GET.get('next', '')

    return render(request, 'login.html', {'next': next_url})


@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def ticket_list(request):
    queryset = Ticket.objects.select_related('author', 'assignee', 'category')
    if request.user.role == User.ROLE_USER:
        queryset = queryset.filter(author=request.user)

    if request.GET.get('status'):
        queryset = queryset.filter(status=request.GET['status'])
    if request.GET.get('priority'):
        queryset = queryset.filter(priority=request.GET['priority'])
    if request.GET.get('category'):
        queryset = queryset.filter(category_id=request.GET['category'])
    if request.GET.get('q'):
        search = request.GET['q'].strip()
        if search.isdecimal():
            queryset = queryset.filter(pk=int(search))
        else:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
    if request.GET.get('assignee') and request.user.role != User.ROLE_USER:
        queryset = queryset.filter(assignee_id=request.GET['assignee'])

    category_choices = Category.objects.all()
    page_obj = Paginator(priority_ordered(queryset), 20).get_page(request.GET.get('page'))
    context = {
        'tickets': page_obj.object_list,
        'page_obj': page_obj,
        'categories': category_choices,
        'technicians': User.objects.filter(
            role__in=(User.ROLE_TECHNICIAN, User.ROLE_ADMIN),
            is_active=True,
        ),
        'ticket_status_choices': Ticket.STATUS_CHOICES,
        'ticket_priority_choices': Ticket.PRIORITY_CHOICES,
        'selected_status': request.GET.get('status', ''),
        'selected_priority': request.GET.get('priority', ''),
        'selected_category': request.GET.get('category', ''),
        'selected_assignee': request.GET.get('assignee', ''),
        'search_query': request.GET.get('q', ''),
        'now': timezone.now(),
    }
    return render(request, 'ticket_list.html', context)


@login_required
def create_ticket(request):
    if request.method == 'POST':
        form = TicketForm(request.POST, user=request.user)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.author = request.user
            ticket.updated_by = request.user
            ticket.save()
            notify_technicians(ticket, 'Byl vytvořen nový požadavek.', actor=request.user)
            messages.success(request, 'Požadavek byl vytvořen.')
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm(user=request.user)

    return render(request, 'ticket_form.html', {'form': form, 'title': 'Nový požadavek'})


@login_required
def ticket_detail(request, pk):
    queryset = Ticket.objects.select_related('author', 'assignee', 'category').prefetch_related('comments__author')
    if request.user.role == User.ROLE_USER:
        queryset = queryset.filter(author=request.user)

    ticket = get_object_or_404(queryset, pk=pk)
    original_status = ticket.status
    original_assignee_id = ticket.assignee_id
    Notification.objects.filter(
        recipient=request.user,
        ticket=ticket,
        read_at__isnull=True,
    ).update(read_at=timezone.now())
    can_manage_ticket = request.user.role in {User.ROLE_TECHNICIAN, User.ROLE_ADMIN}
    comments = ticket.comments.select_related('author').all()
    if not can_manage_ticket:
        comments = comments.filter(is_internal=False)
    history = ticket.history.select_related('changed_by').all()
    attachments = ticket.attachments.select_related('uploaded_by').all()

    comment_form = CommentForm()
    if not can_manage_ticket:
        comment_form.fields.pop('is_internal')
    attachment_form = TicketAttachmentForm()
    status_form = TicketStatusForm(instance=ticket)
    feedback = TicketFeedback.objects.filter(ticket=ticket).first()
    feedback_form = TicketFeedbackForm(instance=feedback) if feedback else TicketFeedbackForm()

    if request.method == 'POST':
        if 'comment_submit' in request.POST:
            comment_form = CommentForm(request.POST)
            if not can_manage_ticket:
                comment_form.fields.pop('is_internal')
            if comment_form.is_valid():
                is_internal = can_manage_ticket and comment_form.cleaned_data.get('is_internal', False)
                Comment.objects.create(
                    ticket=ticket,
                    author=request.user,
                    content=comment_form.cleaned_data['content'],
                    is_internal=is_internal,
                )
                if can_manage_ticket and not is_internal and ticket.first_response_at is None:
                    ticket.first_response_at = timezone.now()
                    ticket.save(update_fields=['first_response_at'])
                if not is_internal:
                    if request.user == ticket.author:
                        if ticket.assignee_id:
                            notify_user(
                                ticket.assignee,
                                ticket,
                                'Uživatel přidal komentář k požadavku.',
                                actor=request.user,
                            )
                        else:
                            notify_technicians(
                                ticket,
                                'Uživatel přidal komentář k požadavku.',
                                actor=request.user,
                            )
                    else:
                        notify_user(
                            ticket.author,
                            ticket,
                            'K požadavku byl přidán nový komentář.',
                            actor=request.user,
                        )
                messages.success(request, 'Komentář byl přidán.')
                return redirect('ticket_detail', pk=ticket.pk)
        elif 'attachment_submit' in request.POST:
            attachment_form = TicketAttachmentForm(request.POST, request.FILES)
            if attachment_form.is_valid():
                attachment = attachment_form.save(commit=False)
                attachment.ticket = ticket
                attachment.uploaded_by = request.user
                attachment.original_name = attachment.file.name
                attachment.save()
                if request.user == ticket.author:
                    if ticket.assignee_id:
                        notify_user(
                            ticket.assignee,
                            ticket,
                            'K požadavku byl přidán soubor.',
                            actor=request.user,
                        )
                    else:
                        notify_technicians(
                            ticket,
                            'K požadavku byl přidán soubor.',
                            actor=request.user,
                        )
                else:
                    notify_user(ticket.author, ticket, 'K požadavku byl přidán soubor.', actor=request.user)
                messages.success(request, 'Příloha byla přidána.')
                return redirect('ticket_detail', pk=ticket.pk)
        elif 'feedback_submit' in request.POST:
            if request.user != ticket.author or ticket.status not in {
                Ticket.STATUS_RESOLVED,
                Ticket.STATUS_CLOSED,
            }:
                raise PermissionDenied
            if feedback is not None:
                messages.error(request, 'Hodnocení tohoto požadavku již bylo odesláno.')
            else:
                feedback_form = TicketFeedbackForm(request.POST)
                if feedback_form.is_valid():
                    feedback = feedback_form.save(commit=False)
                    feedback.ticket = ticket
                    feedback.save()
                    if ticket.assignee_id:
                        notify_user(
                            ticket.assignee,
                            ticket,
                            f'Uživatel ohodnotil řešení známkou {feedback.rating}/5.',
                            actor=request.user,
                        )
                    else:
                        notify_technicians(
                            ticket,
                            f'Uživatel ohodnotil řešení známkou {feedback.rating}/5.',
                            actor=request.user,
                        )
                    messages.success(request, 'Děkujeme za hodnocení řešení.')
                    return redirect('ticket_detail', pk=ticket.pk)
        elif 'status_submit' in request.POST:
            if request.user.role not in {User.ROLE_TECHNICIAN, User.ROLE_ADMIN}:
                raise PermissionDenied
            status_form = TicketStatusForm(request.POST, instance=ticket)
            if status_form.is_valid():
                updated_ticket = status_form.save(commit=False)
                updated_ticket.updated_by = request.user
                updated_ticket.save()
                if original_status != updated_ticket.status:
                    notify_user(
                        ticket.author,
                        ticket,
                        f'Stav požadavku byl změněn na „{updated_ticket.get_status_display()}“.',
                        actor=request.user,
                    )
                if original_assignee_id != updated_ticket.assignee_id and updated_ticket.assignee_id:
                    notify_user(
                        updated_ticket.assignee,
                        ticket,
                        'Byl vám přiřazen požadavek.',
                        actor=request.user,
                    )
                messages.success(request, 'Stav požadavku byl upraven.')
                return redirect('ticket_detail', pk=ticket.pk)
    context = {
        'ticket': ticket,
        'comments': comments,
        'history': history,
        'attachments': attachments,
        'comment_form': comment_form,
        'attachment_form': attachment_form,
        'feedback': feedback,
        'feedback_form': feedback_form,
        'status_form': status_form,
        'can_manage_ticket': can_manage_ticket,
        'can_submit_feedback': (
            request.user == ticket.author
            and ticket.status in {Ticket.STATUS_RESOLVED, Ticket.STATUS_CLOSED}
            and feedback is None
        ),
    }
    return render(request, 'ticket_detail.html', context)


@login_required
def attachment_download(request, pk):
    queryset = TicketAttachment.objects.select_related('ticket', 'ticket__author')
    if request.user.role == User.ROLE_USER:
        queryset = queryset.filter(ticket__author=request.user)
    attachment = get_object_or_404(queryset, pk=pk)
    return FileResponse(
        attachment.file.open('rb'),
        as_attachment=True,
        filename=attachment.original_name,
        content_type='application/octet-stream',
    )


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(recipient=request.user).select_related('ticket')
    return render(request, 'notifications.html', {'notifications': notifications})


@login_required
@require_POST
def mark_notifications_read(request):
    Notification.objects.filter(
        recipient=request.user,
        read_at__isnull=True,
    ).update(read_at=timezone.now())
    messages.success(request, 'Upozornění byla označena jako přečtená.')
    return redirect('notifications')


@login_required
def knowledge_base(request):
    articles = KnowledgeArticle.objects.select_related('category').filter(is_published=True)
    search = request.GET.get('q', '').strip()
    if search:
        articles = articles.filter(Q(title__icontains=search) | Q(content__icontains=search))
    return render(
        request,
        'knowledge_base.html',
        {'articles': articles, 'search_query': search},
    )


@login_required
def knowledge_article_detail(request, slug):
    article = get_object_or_404(KnowledgeArticle.objects.select_related('category'), slug=slug)
    if not article.is_published and request.user.role == User.ROLE_USER:
        raise Http404
    return render(request, 'knowledge_article_detail.html', {'article': article})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_tickets(request):
    queryset = Ticket.objects.select_related('author', 'assignee', 'category')
    if request.user.role == User.ROLE_USER:
        queryset = queryset.filter(author=request.user)

    if request.method == 'GET':
        serializer = TicketSerializer(queryset, many=True)
        return Response(serializer.data)

    serializer = TicketSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        if request.user.role == User.ROLE_USER:
            ticket = serializer.save(
                author=request.user,
                updated_by=request.user,
                status=Ticket.STATUS_NEW,
                priority=Ticket.PRIORITY_NORMAL,
                assignee=None,
            )
        else:
            ticket = serializer.save(author=request.user, updated_by=request.user)
        notify_technicians(ticket, 'Byl vytvořen nový požadavek přes API.', actor=request.user)
        return Response(TicketSerializer(ticket).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def api_ticket_detail(request, pk):
    queryset = Ticket.objects.select_related('author', 'assignee', 'category')
    if request.user.role == User.ROLE_USER:
        queryset = queryset.filter(author=request.user)

    ticket = get_object_or_404(queryset, pk=pk)

    if request.method == 'GET':
        serializer = TicketSerializer(ticket)
        return Response(serializer.data)

    if request.method == 'DELETE':
        if request.user.role != User.ROLE_ADMIN:
            return Response({'detail': 'Nemáte oprávnění smazat tento požadavek.'}, status=status.HTTP_403_FORBIDDEN)
        ticket.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.user.role not in {User.ROLE_TECHNICIAN, User.ROLE_ADMIN}:
        return Response({'detail': 'Nemáte oprávnění upravovat tento požadavek.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = TicketSerializer(ticket, data=request.data, partial=(request.method == 'PATCH'))
    if serializer.is_valid():
        previous_status = ticket.status
        previous_assignee_id = ticket.assignee_id
        ticket = serializer.save(updated_by=request.user)
        if previous_status != ticket.status:
            notify_user(
                ticket.author,
                ticket,
                f'Stav požadavku byl změněn na „{ticket.get_status_display()}“.',
                actor=request.user,
            )
        if previous_assignee_id != ticket.assignee_id and ticket.assignee_id:
            notify_user(ticket.assignee, ticket, 'Byl vám přiřazen požadavek.', actor=request.user)
        return Response(TicketSerializer(ticket).data)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
