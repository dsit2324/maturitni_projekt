from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .forms import CommentForm, RegisterForm, TicketForm, TicketStatusForm
from .models import Category, Comment, Ticket, User
from .serializers import TicketSerializer


@login_required
def dashboard(request):
    queryset = Ticket.objects.select_related('author', 'assignee', 'category')
    if request.user.role == User.ROLE_USER:
        queryset = queryset.filter(author=request.user)

    total = queryset.count()
    new = queryset.filter(status=Ticket.STATUS_NEW).count()
    in_progress = queryset.filter(status=Ticket.STATUS_IN_PROGRESS).count()
    resolved = queryset.filter(status=Ticket.STATUS_RESOLVED).count()
    critical = queryset.filter(priority=Ticket.PRIORITY_CRITICAL).count()
    recent = queryset.order_by('-created_at')[:5]

    context = {
        'total_tickets': total,
        'new_tickets': new,
        'in_progress_tickets': in_progress,
        'resolved_tickets': resolved,
        'critical_tickets': critical,
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
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Neplatné přihlašovací údaje.')

    return render(request, 'login.html')


@login_required
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

    category_choices = Category.objects.all()
    context = {
        'tickets': queryset.order_by('-created_at'),
        'categories': category_choices,
        'ticket_status_choices': Ticket.STATUS_CHOICES,
        'ticket_priority_choices': Ticket.PRIORITY_CHOICES,
        'selected_status': request.GET.get('status', ''),
        'selected_priority': request.GET.get('priority', ''),
        'selected_category': request.GET.get('category', ''),
    }
    return render(request, 'ticket_list.html', context)


@login_required
def create_ticket(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.author = request.user
            ticket.save()
            messages.success(request, 'Požadavek byl vytvořen.')
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketForm()

    return render(request, 'ticket_form.html', {'form': form, 'title': 'Nový požadavek'})


@login_required
def ticket_detail(request, pk):
    queryset = Ticket.objects.select_related('author', 'assignee', 'category').prefetch_related('comments__author')
    if request.user.role == User.ROLE_USER:
        queryset = queryset.filter(author=request.user)

    ticket = get_object_or_404(queryset, pk=pk)
    comments = ticket.comments.select_related('author').all()

    comment_form = CommentForm()
    status_form = TicketStatusForm(instance=ticket)

    if request.method == 'POST':
        if 'comment_submit' in request.POST:
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                Comment.objects.create(
                    ticket=ticket,
                    author=request.user,
                    content=comment_form.cleaned_data['content'],
                )
                messages.success(request, 'Komentář byl přidán.')
                return redirect('ticket_detail', pk=ticket.pk)
        elif 'status_submit' in request.POST:
            status_form = TicketStatusForm(request.POST, instance=ticket)
            if status_form.is_valid():
                updated_ticket = status_form.save(commit=False)
                if updated_ticket.status == Ticket.STATUS_RESOLVED and not updated_ticket.resolved_at:
                    updated_ticket.resolved_at = timezone.now()
                elif updated_ticket.status != Ticket.STATUS_RESOLVED:
                    updated_ticket.resolved_at = None
                updated_ticket.save()
                messages.success(request, 'Stav požadavku byl upraven.')
                return redirect('ticket_detail', pk=ticket.pk)

    context = {
        'ticket': ticket,
        'comments': comments,
        'comment_form': comment_form,
        'status_form': status_form,
    }
    return render(request, 'ticket_detail.html', context)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_tickets(request):
    queryset = Ticket.objects.select_related('author', 'assignee', 'category')
    if request.user.role == User.ROLE_USER:
        queryset = queryset.filter(author=request.user)

    if request.method == 'GET':
        serializer = TicketSerializer(queryset, many=True)
        return Response(serializer.data)

    serializer = TicketSerializer(data=request.data)
    if serializer.is_valid():
        ticket = serializer.save(author=request.user)
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
        ticket.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = TicketSerializer(ticket, data=request.data, partial=(request.method == 'PATCH'))
    if serializer.is_valid():
        if request.user.role in {User.ROLE_TECHNICIAN, User.ROLE_ADMIN}:
            if 'status' in request.data or 'priority' in request.data or 'assignee' in request.data:
                ticket = serializer.save()
                if ticket.status == Ticket.STATUS_RESOLVED and not ticket.resolved_at:
                    ticket.resolved_at = timezone.now()
                elif ticket.status != Ticket.STATUS_RESOLVED:
                    ticket.resolved_at = None
                ticket.save()
                return Response(TicketSerializer(ticket).data)

        if request.user.role == User.ROLE_USER:
            serializer.save()
            return Response(TicketSerializer(ticket).data)

        return Response({'detail': 'Nemáte oprávnění upravovat tento požadavek.'}, status=status.HTTP_403_FORBIDDEN)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
