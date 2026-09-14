from rest_framework import serializers

from .models import Category, Ticket, User


class TicketSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    assignee = serializers.StringRelatedField(read_only=True)
    category = serializers.StringRelatedField(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(source='category', queryset=Category.objects.all(), write_only=True, required=False)
    assignee_id = serializers.PrimaryKeyRelatedField(source='assignee', queryset=User.objects.all(), write_only=True, required=False, allow_null=True)

    class Meta:
        model = Ticket
        fields = (
            'id',
            'title',
            'description',
            'author',
            'assignee',
            'category',
            'category_id',
            'assignee_id',
            'status',
            'priority',
            'created_at',
            'updated_at',
            'resolved_at',
        )
        read_only_fields = ('id', 'author', 'created_at', 'updated_at', 'resolved_at')
