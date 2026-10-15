import hashlib
from datetime import timedelta

from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from core.models import PageText, SiteProfile

from .forms import ContactForm
from .models import ContactSubmission

RATE_LIMIT = 3  # messages per address per hour


def ip_hash(request):
    # behind Nginx the last X-Forwarded-For entry is the one Nginx added; earlier ones can be faked by the client
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    ip = forwarded.split(',')[-1].strip() if forwarded else request.META.get('REMOTE_ADDR', '')
    return hashlib.sha256(f'{settings.SECRET_KEY}:{ip}'.encode()).hexdigest()


def index(request):
    form = ContactForm(request.POST or None)
    sent_url = reverse('contact:index') + '?sent=1'
    if request.method == 'POST' and form.is_valid():
        if form.is_spam():
            return redirect(sent_url)  # look successful, keep nothing
        key = ip_hash(request)
        recent = ContactSubmission.objects.filter(ip_hash=key, created_at__gte=timezone.now() - timedelta(hours=1))
        if recent.count() >= RATE_LIMIT:
            form.add_error(None, 'Too many messages from your connection in the last hour. Try again later, or email me directly.')
        else:
            submission = form.save(commit=False)
            submission.ip_hash = key
            submission.save()
            return redirect(sent_url)
    return render(request, 'contact/index.html', {
        'meta_title': 'Contact', 'heading': 'Contact',
        **PageText.context(PageText.Page.CONTACT, SiteProfile.load()),
        'hide_cta': True, 'form': form, 'sent': request.GET.get('sent') == '1',
    })
