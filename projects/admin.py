from django.contrib import admin

from core.widgets import MarkdownAdminMixin

from .models import Decision, Project


class DecisionInline(admin.TabularInline):
    model = Decision
    extra = 1
    fields = ['decision', 'why', 'tradeoff', 'order']


@admin.register(Project)
class ProjectAdmin(MarkdownAdminMixin, admin.ModelAdmin):
    markdown_fields = ['problem', 'approach', 'result']
    list_display = ['title', 'year', 'status', 'featured', 'order']
    list_editable = ['status', 'featured', 'order']
    list_filter = ['status', 'featured']
    search_fields = ['title', 'summary', 'stack']
    prepopulated_fields = {'slug': ['title']}
    inlines = [DecisionInline]
    fieldsets = [
        (None, {'fields': ['title', 'slug', 'summary', 'year', 'role', 'stack']}),
        ('Case study', {'fields': ['problem', 'approach', 'result'],
                        'description': 'Markdown. Key decisions are listed below the form.'}),
        ('Diagram', {'fields': ['diagram', 'diagram_caption']}),
        ('Links', {'fields': ['source_url', 'demo_url', 'availability_note'],
                   'description': 'Links are optional and only shown when set. Without one, the note explains why.'}),
        ('Publishing', {'fields': ['status', 'featured', 'order']}),
    ]
