from django.db import migrations

FOCUS_AREAS = [
    ('Backend engineering', 'APIs, data models and services built to run in production.'),
    ('AI/ML systems', 'Putting models behind reliable, observable interfaces.'),
    ('System design', 'Trade-offs, scaling and failure modes before code.'),
    ('Software architecture', 'Boundaries that keep systems maintainable as they grow.'),
    ('APIs & distributed systems', 'Contracts, consistency and communication between services.'),
    ('Production engineering', 'Deployment, monitoring and keeping things running.'),
]


def seed(apps, schema_editor):
    """Starter content for a new install, so every page renders. Replace it in admin (Site profile, Focus areas)."""
    SiteProfile = apps.get_model('core', 'SiteProfile')
    FocusArea = apps.get_model('core', 'FocusArea')

    SiteProfile.objects.get_or_create(
        pk=1,
        defaults={
            'name': 'Your Name',
            'role': 'Your role',
            'highlights': 'what you build\nwhat you know\nwhat you care about',
            'tagline': 'One or two sentences about the work you do and who it is for.',
            'availability': '',
            'meta_description': 'Your Name, your role. One sentence for search results about the work you do.',
        },
    )
    if not FocusArea.objects.exists():
        FocusArea.objects.bulk_create(
            FocusArea(title=title, description=description, order=i)
            for i, (title, description) in enumerate(FOCUS_AREAS)
        )
    # one empty row per fixed page, editable in admin; empty fields mean "use the default"
    PageText = apps.get_model('core', 'PageText')
    for page in ['about', 'projects', 'blog', 'resume', 'contact']:
        PageText.objects.get_or_create(page=page)


class Migration(migrations.Migration):
    dependencies = [('core', '0001_initial')]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
