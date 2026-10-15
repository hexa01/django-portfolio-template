from django import forms

from .models import ContactSubmission


class ContactForm(forms.ModelForm):
    # honeypot: hidden from people, filled in by bots
    website = forms.CharField(required=False)

    class Meta:
        model = ContactSubmission
        fields = ['name', 'email', 'subject', 'message']
        error_messages = {
            'name': {'required': 'Add your name.'},
            'email': {'required': 'Add an email address so I can reply.', 'invalid': 'Check the email address.'},
            'message': {'required': 'Write a short message.'},
        }

    def clean_message(self):
        message = self.cleaned_data['message'].strip()
        if len(message) < 10:
            raise forms.ValidationError('Add a little more detail (at least 10 characters).')
        return message

    def is_spam(self):
        return bool(self.cleaned_data.get('website'))
