from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html

from .models import Certification, Education, Experience, FocusArea, PageText, SiteProfile, SkillGroup, SocialLink
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
