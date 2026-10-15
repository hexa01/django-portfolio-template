from django.contrib import admin
from django.utils.html import format_html, format_html_join

from core.widgets import MarkdownAdminMixin

from .models import Category, Post, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order']
    list_editable = ['order']
    prepopulated_fields = {'slug': ['name']}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name']
    prepopulated_fields = {'slug': ['name']}


@admin.register(Post)
class PostAdmin(MarkdownAdminMixin, admin.ModelAdmin):
    markdown_fields = ['body']
    list_display = ['title', 'status', 'published_at', 'category', 'reading_minutes', 'checks_passed']
    list_filter = ['status', 'category', 'tags']
    search_fields = ['title', 'excerpt', 'body']
    date_hierarchy = 'published_at'
    prepopulated_fields = {'slug': ['title']}
    filter_horizontal = ['tags']
    readonly_fields = ['checklist_display', 'reading_minutes']
    fieldsets = [
        (None, {'fields': ['title', 'slug', 'excerpt', 'body']}),
        ('Cover', {'fields': ['cover', 'cover_alt'], 'classes': ['collapse']}),
        ('Topics', {'fields': ['category', 'tags']}),
        ('Publishing', {'fields': ['status', 'published_at', 'updated_at', 'canonical_url', 'reading_minutes']}),
        ('Search engines', {'fields': ['seo_title', 'seo_description'], 'classes': ['collapse']}),
        ('Editorial checklist', {'fields': ['checklist_display'],
                                 'description': 'Suggestions only. They never stop you saving or publishing.'}),
    ]

    @admin.display(description='Checklist')
    def checks_passed(self, post):
        checks = post.checklist()
        return f'{sum(ok for _, ok in checks)} / {len(checks)}'

    @admin.display(description='Checks')
    def checklist_display(self, post):
        if not post.pk:
            return 'Shown after the first save.'
        return format_html('<ul style="margin:0;padding:0;list-style:none">{}</ul>', format_html_join(
            '', '<li>{} {}</li>', (('✓' if ok else '○', label) for label, ok in post.checklist()),
        ))
