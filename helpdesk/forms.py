from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Comment, Ticket, User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('title', 'description', 'category', 'priority')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('content',)
        labels = {'content': 'Komentář'}
        widgets = {'content': forms.Textarea(attrs={'rows': 3})}


class TicketStatusForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assignee'].queryset = User.objects.filter(role=User.ROLE_TECHNICIAN)

    class Meta:
        model = Ticket
        fields = ('status', 'priority', 'assignee')
        labels = {'status': 'Stav', 'priority': 'Priorita', 'assignee': 'Technik'}
