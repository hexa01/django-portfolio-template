"""Markdown fields in admin: a plain textarea that markdown-editor.js turns into a toolbar + preview editor."""

from django import forms
from django.urls import reverse_lazy


class MarkdownWidget(forms.Textarea):
    class Media:
        css = {'all': ['css/markdown-editor.css']}
        js = ['js/markdown-editor.js']

    def __init__(self, attrs=None):
        super().__init__({'data-markdown': '', 'data-preview-url': reverse_lazy('markdown-preview'), 'rows': 20, **(attrs or {})})


class MarkdownAdminMixin:
    """List the Markdown fields in `markdown_fields` to give them the editor."""

    markdown_fields = ()

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in self.markdown_fields:
            kwargs['widget'] = MarkdownWidget
        return super().formfield_for_dbfield(db_field, request, **kwargs)
