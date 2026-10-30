from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from core import og, seo
from core.models import PageText, SiteProfile

from .models import Project


def index(request):
    projects = list(Project.objects.published().prefetch_related('decisions'))
    featured = next((p for p in projects if p.featured), projects[0] if projects else None)
    return render(request, 'projects/index.html', {
        'meta_title': 'Projects', 'heading': 'Projects',
        **PageText.context(PageText.Page.PROJECTS, SiteProfile.load()),
        'featured': featured,
        'projects': [p for p in projects if p is not featured],
    })


def detail(request, slug):
    project = get_object_or_404(Project.objects.published(), slug=slug)
    schema = [seo.breadcrumbs(request, ('Home', reverse('core:home')), ('Projects', reverse('projects:index')),
                              (project.title, project.get_absolute_url()))]
    if project.source_url:
        schema.append(seo.source_code(request, project, SiteProfile.load()))
    return render(request, 'projects/detail.html', {
        'meta_title': project.title, 'meta_description': project.summary,
        'og_image': og.url(request, 'core:og-project', project.slug, project.title),
        'schema': schema,
        'project': project,
        'others': Project.objects.published().exclude(pk=project.pk)[:2],
    })
