from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.checks import Error, register


@register()
def theme_exists(app_configs, **kwargs):
    if finders.find(f'css/themes/{settings.SITE_THEME}.css'):
        return []
    return [Error(
        f'SITE_THEME = {settings.SITE_THEME!r} but static/css/themes/{settings.SITE_THEME}.css does not exist.',
        id='core.E001',
    )]
