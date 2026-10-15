from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ContactSubmission

PLAIN_STATIC = override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
)

VALID = {'name': 'Ada', 'email': 'ada@example.com', 'subject': 'A project', 'message': 'I have a backend to build.'}


@PLAIN_STATIC
class ContactTests(TestCase):
    url = reverse('contact:index')

    def test_form_renders_with_csrf_and_labels(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, '<label for="id_email">Email</label>', html=True)

    def test_valid_message_is_saved_and_confirmed(self):
        response = self.client.post(self.url, VALID, follow=True)
        self.assertRedirects(response, self.url + '?sent=1')
        self.assertContains(response, 'Message sent')
        submission = ContactSubmission.objects.get()
        self.assertEqual(submission.email, 'ada@example.com')
        self.assertEqual(len(submission.ip_hash), 64)  # hashed, never the raw address
        self.assertNotIn('127.0.0.1', submission.ip_hash)

    def test_invalid_input_shows_inline_errors_and_saves_nothing(self):
        response = self.client.post(self.url, {**VALID, 'email': 'not-an-email', 'message': 'hi'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Check the email address.')
        self.assertContains(response, 'at least 10 characters')
        self.assertContains(response, 'aria-invalid="true"')
        self.assertContains(response, 'value="Ada"')  # what was typed is kept
        self.assertFalse(ContactSubmission.objects.exists())

    def test_honeypot_looks_successful_but_saves_nothing(self):
        response = self.client.post(self.url, {**VALID, 'website': 'https://spam.example'})
        self.assertRedirects(response, self.url + '?sent=1')
        self.assertFalse(ContactSubmission.objects.exists())

    def test_rate_limit_per_address(self):
        for _ in range(3):
            self.client.post(self.url, VALID)
        response = self.client.post(self.url, VALID)
        self.assertContains(response, 'Too many messages')
        self.assertEqual(ContactSubmission.objects.count(), 3)
        # a different address is unaffected
        self.client.post(self.url, VALID, REMOTE_ADDR='10.0.0.9')
        self.assertEqual(ContactSubmission.objects.count(), 4)
