import json

from django import template
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

# the same escaping as Django's json_script, so text from admin can't close the <script> tag
ESCAPES = {ord('>'): '\\u003E', ord('<'): '\\u003C', ord('&'): '\\u0026'}


@register.filter
def jsonld(data):
    """A schema.org dict as a <script type="application/ld+json"> tag."""
    return format_html('<script type="application/ld+json">{}</script>',
                       mark_safe(json.dumps(data, cls=DjangoJSONEncoder, ensure_ascii=False).translate(ESCAPES)))
