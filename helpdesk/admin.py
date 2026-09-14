from django.contrib import admin

from .models import Category, Comment, Ticket, TicketSolution, User


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
    list_display = ('ticket', 'author', 'created_at')
    search_fields = ('content',)


@admin.register(TicketSolution)
class TicketSolutionAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'technician', 'created_at')
    search_fields = ('content',)
