from django.contrib import admin

from .models import (
    Category,
    Comment,
    KnowledgeArticle,
    Notification,
    Ticket,
    TicketAttachment,
    TicketFeedback,
    TicketSolution,
    User,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_staff')
    list_filter = ('role', 'is_staff')
    search_fields = ('username', 'email')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'priority', 'author', 'assignee', 'created_at')
    list_filter = ('status', 'priority', 'category')
    search_fields = ('title', 'description', 'author__username')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'is_internal', 'created_at')
    search_fields = ('content',)
    list_filter = ('is_internal',)


@admin.register(TicketSolution)
class TicketSolutionAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'technician', 'created_at')
    search_fields = ('content',)


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'ticket', 'uploaded_by', 'created_at')
    search_fields = ('original_name', 'ticket__title')


@admin.register(TicketFeedback)
class TicketFeedbackAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'rating', 'submitted_at')
    list_filter = ('rating',)
    search_fields = ('ticket__title', 'comment')


@admin.register(KnowledgeArticle)
class KnowledgeArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_published', 'updated_at')
    list_filter = ('is_published', 'category')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'ticket', 'message', 'created_at', 'read_at')
    list_filter = ('read_at', 'created_at')
    search_fields = ('recipient__username', 'ticket__title', 'message')
