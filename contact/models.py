from django.db import models


class ContactSubmission(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=150, blank=True)
    message = models.TextField(max_length=5000)
    ip_hash = models.CharField(max_length=64, editable=False, help_text='Hashed, for rate limiting only.')
    is_read = models.BooleanField('read', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name}: {self.subject or self.message[:40]}'
