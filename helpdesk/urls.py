from django.urls import path

from .views import (
    api_ticket_detail,
    api_tickets,
    create_ticket,
    dashboard,
    login_view,
    logout_view,
    register_view,
    ticket_detail,
    ticket_list,
)

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('tickets/', ticket_list, name='ticket_list'),
    path('tickets/new/', create_ticket, name='create_ticket'),
    path('tickets/<int:pk>/', ticket_detail, name='ticket_detail'),
    path('api/tickets/', api_tickets, name='api_tickets'),
    path('api/tickets/<int:pk>/', api_ticket_detail, name='api_ticket_detail'),
]
