from django.contrib.admin.views.decorators import staff_member_required
from django.db import DatabaseError, connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView

from blog.models import Post
from projects.models import Project

from .models import Certification, Education, Experience, FocusArea, PageText, SiteProfile, SkillGroup
from . import og, seo
from .text import render_article
from .theme import theme_colors


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['focus_areas'] = FocusArea.objects.all()
        published = Project.objects.published()
        context['projects'] = list(published.filter(featured=True)[:2]) or list(published[:2])
        context['posts'] = Post.objects.published()[:3]
        profile = SiteProfile.load()
        context['schema'] = [seo.website(self.request, profile), seo.person(self.request, profile)]
        return context


@require_GET
@never_cache
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except DatabaseError:
        return JsonResponse({'status': 'error'}, status=503)
    return JsonResponse({'status': 'ok'})


@require_GET
@cache_control(max_age=3600)
def favicon(request):
    """Initials on the accent colour, so the tab icon follows the profile (unless a logo is uploaded)."""
    profile = SiteProfile.load()
    context = {
        'initials': profile.initials,
        'accent': theme_colors()['dark']['accent'],
        'ink': theme_colors()['dark']['bg'],
    }
    return render(request, 'favicon.svg', context, content_type='image/svg+xml')


class AboutView(TemplateView):
    template_name = 'core/about.html'
    extra_context = {'meta_title': 'About', 'heading': 'About'}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = SiteProfile.load()
        context.update(PageText.context(PageText.Page.ABOUT, profile))
        # the resume entry without an end year is the current job
        context['current_job'] = Experience.objects.filter(end_year__isnull=True).first()
        context['schema'] = [seo.person(self.request, profile)]
        return context


class ResumeView(TemplateView):
    template_name = 'core/resume.html'
    extra_context = {'meta_title': 'Resume', 'heading': 'Resume'}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(PageText.context(PageText.Page.RESUME, SiteProfile.load()))
        context.update(
            experience=Experience.objects.all(), education=Education.objects.all(), skills=SkillGroup.objects.all(),
            certifications=Certification.objects.all(),
        )
        return context


def search(request):
    """Projects and posts. A page of its own without JS; the header search panel loads just the results (?panel=1)."""
    query = request.GET.get('q', '').strip()[:100]
    panel = 'panel' in request.GET
    limit = 5 if panel else 20
    projects = posts = []
    if len(query) >= 2:
        projects = Project.objects.published().search(query)[:limit]
        posts = Post.objects.published().search(query)[:limit]
    context = {'query': query, 'projects': projects, 'posts': posts}
    if panel:
        return render(request, 'core/_search_results.html', context)
    return render(request, 'core/search.html', {
        **context, 'meta_title': 'Search', 'heading': 'Search', 'noindex': True, 'hide_cta': True,
        'lead': 'Find projects and posts.',
    })


@staff_member_required
@require_POST
def markdown_preview(request):
    """The admin editor's Preview tab: the same rendering the site uses, for staff only."""
    html, _, _ = render_article(request.POST.get('text', '')[:200_000])
    return HttpResponse(html)


def _card(title, kicker):
    profile = SiteProfile.load()
    return HttpResponse(og.card(title, kicker, profile.name, profile.initials), content_type='image/png')


@require_GET
@cache_control(max_age=86400)
def og_site(request):
    profile = SiteProfile.load()
    return _card(profile.tagline or profile.role or profile.name, profile.role)


@require_GET
@cache_control(max_age=86400)
def og_project(request, slug):
    project = get_object_or_404(Project.objects.published(), slug=slug)
    return _card(project.title, 'Project')


@require_GET
@cache_control(max_age=86400)
def og_post(request, slug):
    post = get_object_or_404(Post.objects.published(), slug=slug)
    return _card(post.title, 'Blog')
