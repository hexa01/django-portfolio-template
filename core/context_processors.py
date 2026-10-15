from django.urls import reverse

from django.conf import settings

from .models import SiteProfile
from .theme import theme_colors

NAV_ITEMS = [
    ('Home', 'core:home'),
    ('About', 'core:about'),
    ('Projects', 'projects:index'),
    ('Blog', 'blog:index'),
    ('Resume', 'core:resume'),
    ('Contact', 'contact:index'),
]


def site(request):
    match = request.resolver_match
    current = match.view_name if match else ''
    section = match.namespace if match else ''

    nav = []
    for label, view_name in NAV_ITEMS:
        namespace = view_name.split(':')[0]
        # core pages match exactly; other apps are active anywhere in their section
        active = current == view_name if namespace == 'core' else section == namespace
        nav.append({'label': label, 'url': reverse(view_name), 'active': active})

    profile = SiteProfile.load()
    return {
        'nav_items': nav,
        'profile': profile,
        'site_indexable': settings.SITE_INDEXABLE,
        # the preview card for pages without their own (see core/og.py)
        'og_default': request.build_absolute_uri(reverse('core:og-site')) + f'?v={profile.updated_at:%Y%m%d%H%M%S}',
        'theme': theme_colors(),
        'theme_css': f'css/themes/{settings.SITE_THEME}.css',
    }
