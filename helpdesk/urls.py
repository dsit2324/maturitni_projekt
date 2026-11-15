from django.urls import path

from .views import (
    api_ticket_detail,
    api_tickets,
    attachment_download,
    create_ticket,
    dashboard,
    knowledge_article_detail,
    knowledge_base,
    login_view,
    logout_view,
    mark_notifications_read,
    notification_list,
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
    path('attachments/<int:pk>/', attachment_download, name='attachment_download'),
    path('notifications/', notification_list, name='notifications'),
    path('notifications/read-all/', mark_notifications_read, name='mark_notifications_read'),
    path('knowledge/', knowledge_base, name='knowledge_base'),
    path('knowledge/<slug:slug>/', knowledge_article_detail, name='knowledge_article_detail'),
    path('api/tickets/', api_tickets, name='api_tickets'),
    path('api/tickets/<int:pk>/', api_ticket_detail, name='api_ticket_detail'),
]
