"""Structured data (schema.org JSON-LD) for search engines. Views add a `schema` list; base.html prints each item."""

from django.urls import reverse


def _url(request, path):
    return request.build_absolute_uri(path)


def person(request, profile):
    data = {
        '@context': 'https://schema.org', '@type': 'Person',
        'name': profile.name, 'url': _url(request, reverse('core:home')),
    }
    if profile.role:
        data['jobTitle'] = profile.role
    if profile.photo:
        data['image'] = _url(request, profile.photo.url)
    if profile.location:
        data['homeLocation'] = {'@type': 'Place', 'name': profile.location}
    from .models import Experience  # the resume entry without an end year is the current job
    if job := Experience.objects.filter(end_year__isnull=True).first():
        data['worksFor'] = {'@type': 'Organization', 'name': job.organization}
    links = [link.url for link in profile.social_links.all()]
    if links:
        data['sameAs'] = links
    return data


def website(request, profile):
    return {
        '@context': 'https://schema.org', '@type': 'WebSite',
        'name': profile.name, 'url': _url(request, reverse('core:home')),
        'potentialAction': {
            '@type': 'SearchAction',
            'target': _url(request, reverse('core:search')) + '?q={query}',
            'query-input': 'required name=query',
        },
    }


def article(request, post, profile, image):
    data = {
        '@context': 'https://schema.org', '@type': 'BlogPosting',
        'headline': post.title, 'description': post.excerpt,
        'url': _url(request, post.get_absolute_url()),
        'mainEntityOfPage': post.canonical_url or _url(request, post.get_absolute_url()),
        'datePublished': post.published_at.isoformat() if post.published_at else None,
        'dateModified': (post.updated_at or post.published_at).isoformat() if post.published_at else None,
        'author': {'@type': 'Person', 'name': profile.name, 'url': _url(request, reverse('core:home'))},
        'image': image,
        'keywords': [tag.name for tag in post.tags.all()],
    }
    return {key: value for key, value in data.items() if value}


def source_code(request, project, profile):
    """For a project with public code: the case study and the repository describe the same software, by the owner."""
    return {
        '@context': 'https://schema.org', '@type': 'SoftwareSourceCode',
        'name': project.title, 'description': project.summary,
        'url': _url(request, project.get_absolute_url()),
        'codeRepository': project.source_url,
        'keywords': project.stack_list,
        'author': {'@type': 'Person', 'name': profile.name, 'url': _url(request, reverse('core:home'))},
    }


def breadcrumbs(request, *trail):
    """trail: (name, path) pairs from the home page down to the current page."""
    return {
        '@context': 'https://schema.org', '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': i, 'name': name, 'item': _url(request, path)}
            for i, (name, path) in enumerate(trail, start=1)
        ],
    }
