from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join

from .models import (
    Certification, Education, Experience, FocusArea, Image, PageText, SiteProfile, SkillGroup, SocialLink,
)
from .theme import theme_colors
from .widgets import MarkdownAdminMixin


class SocialLinkInline(admin.TabularInline):
    model = SocialLink
    extra = 0
    fields = ['label', 'url', 'order']


@admin.register(SiteProfile)
class SiteProfileAdmin(MarkdownAdminMixin, admin.ModelAdmin):
    markdown_fields = ['bio', 'how_i_work', 'now']
    inlines = [SocialLinkInline]
    readonly_fields = ['logo_preview']
    fieldsets = [
        (None, {'fields': ['name', 'role', 'highlights', 'tagline', 'availability']}),
        ('Logo', {'fields': ['logo', 'logo_preview']}),
        ('Contact', {'fields': ['email']}),
        ('About page', {'fields': ['photo', 'location', 'bio', 'how_i_work', 'now'],
                        'description': 'Bio, principles and "now" are Markdown.'}),
        ('Resume page', {'fields': ['resume_pdf'],
                         'description': 'Experience, education and skills are edited in their own lists.'}),
        ('Search & sharing', {'fields': ['meta_description']}),
    ]

    @admin.display(description='In the header')
    def logo_preview(self, obj):
        dark = theme_colors()['dark']
        if obj and obj.logo:
            mark = format_html('<img src="{}" width="26" height="26" style="border-radius:6px;object-fit:cover">', obj.logo.url)
        else:
            mark = format_html(
                '<span style="display:inline-grid;place-items:center;width:26px;height:26px;border-radius:5px;'
                'background:{};color:{};font:600 11px monospace">{}</span>',
                dark['accent'], dark['bg'], obj.initials if obj else '?',
            )
        return format_html(
            '<span style="display:inline-flex;align-items:center;gap:10px;padding:10px 14px;background:{};'
            'border-radius:6px;color:{};font-weight:600">{} {}</span>'
            '<p class="help">Without a logo, your initials are used. Save to update.</p>',
            dark['bg'], dark['text'], mark, obj.name if obj else '',
        )

    def has_add_permission(self, request):
        return not SiteProfile.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # there is only one profile: go straight to it
        profile = SiteProfile.load()
        return redirect(reverse('admin:core_siteprofile_change', args=[profile.pk]))


@admin.register(PageText)
class PageTextAdmin(admin.ModelAdmin):
    list_display = ['page', 'seo_title', 'intro_preview', 'description_length']
    readonly_fields = ['page']
    fields = ['page', 'seo_title', 'lead', 'meta_description']

    @admin.display(description='Intro')
    def intro_preview(self, obj):
        return obj.lead or '(standard line)'

    @admin.display(description='Search description')
    def description_length(self, obj):
        return f'{len(obj.meta_description)} characters' if obj.meta_description else '(generated)'

    # one row per page, created by a migration: edit only
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FocusArea)
class FocusAreaAdmin(admin.ModelAdmin):
    list_display = ['title', 'description', 'order']
    list_editable = ['order']


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ['role', 'organization', 'period', 'order']
    list_editable = ['order']
    search_fields = ['role', 'organization']


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ['title', 'organization', 'period', 'order']
    list_editable = ['order']


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ['name', 'issuer', 'year', 'valid_until', 'order']
    list_editable = ['order']


@admin.register(SkillGroup)
class SkillGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'items', 'order']
    list_editable = ['order']


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ['thumbnail', 'alt', 'dimensions', 'created_at']
    list_display_links = ['thumbnail', 'alt']
    search_fields = ['alt', 'file']
    fields = ['file', 'alt', 'preview', 'markdown_line', 'used_in']
    readonly_fields = ['preview', 'markdown_line', 'used_in']

    @admin.display(description='')
    def thumbnail(self, obj):
        return format_html('<img src="{}" alt="" style="width:88px;height:56px;object-fit:cover;border-radius:4px">',
                           obj.file.url)

    @admin.display(description='Size')
    def dimensions(self, obj):
        return f'{obj.width} × {obj.height}' if obj.width else 'SVG'

    @admin.display(description='Preview')
    def preview(self, obj):
        if not obj or not obj.file:
            return 'Shown after saving.'
        return format_html('<img src="{}" alt="" style="max-width:420px;max-height:280px;border-radius:6px">',
                           obj.file.url)

    @admin.display(description='Markdown')
    def markdown_line(self, obj):
        if not obj or not obj.file:
            return 'Shown after saving.'
        return format_html('<div><code style="user-select:all">{}</code></div>'
                           '<div style="margin-top:4px;color:var(--body-quiet-color);font-size:.8125rem">'
                           'Click once to select it, then paste it into a post or project text, or use the editor\'s '
                           'Image button.</div>', obj.markdown)

    @admin.display(description='Used in')
    def used_in(self, obj):
        usages = obj.usages() if obj and obj.pk else []
        if not usages:
            return 'Not used in any post, project or About text yet.'
        return format_html_join(format_html('<br>'), '<a href="{}">{}</a>', ((url, label) for label, url in usages))

    def delete_view(self, request, object_id, extra_context=None):
        obj = self.get_object(request, object_id)
        if obj and request.method == 'GET' and (usages := obj.usages()):
            messages.warning(request, f'This image is still shown in: {", ".join(label for label, _ in usages)}. '
                                      'Deleting it leaves a broken image there.')
        return super().delete_view(request, object_id, extra_context)
