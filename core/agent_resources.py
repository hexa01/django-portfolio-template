"""What AI agents may edit in core: the site profile and the fixed pages' texts (through agent_content's API)."""

from agent_content import Resource, register

from .models import PageText, SiteProfile

register(Resource(
    SiteProfile,
    name='profile',
    description='The site owner\'s profile: role, tagline, highlights (one per line) and the About page text (Markdown). '
                'meta_description is the home page\'s search description.',
    singleton=SiteProfile.load,
    fields=['role', 'highlights', 'tagline', 'availability', 'bio', 'how_i_work', 'now', 'meta_description'],
    read_only=['name', 'email', 'location'],
))

register(Resource(
    PageText,
    name='pages',
    singular='page',
    description='SEO title, intro line and search description of the fixed pages (about, projects, blog, resume, '
                'contact). Leave a field empty to use the standard default. Titles up to 70 characters, '
                'descriptions 120-160 and unique per page.',
    lookup='page',
    fields=['seo_title', 'lead', 'meta_description'],
    read_only=['page'],
    list_fields=['page', 'seo_title', 'meta_description'],
))
