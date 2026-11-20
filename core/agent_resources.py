"""What AI agents may edit in core: the site profile, the fixed pages' texts and the image library
(through agent_content's API)."""

from agent_content import Resource, Upload, register

from .media import MAX_UPLOAD_BYTES
from .models import Education, Experience, Image, PageText, SiteProfile

IMAGES = Upload(accept=['image/'], max_bytes=MAX_UPLOAD_BYTES)

register(Resource(
    SiteProfile,
    name='profile',
    description='The site owner\'s profile: role, tagline, highlights (one per line) and the About page text (Markdown). '
                'meta_description is the home page\'s search description. Upload only a photo, logo or resume the '
                'owner provides.',
    singleton=SiteProfile.load,
    fields=['role', 'highlights', 'tagline', 'availability', 'bio', 'how_i_work', 'now', 'meta_description'],
    read_only=['name', 'email', 'location'],
    uploads={
        'photo': IMAGES,
        'logo': IMAGES,
        'resume_pdf': Upload(accept=['application/pdf'], max_bytes=MAX_UPLOAD_BYTES),
    },
))

RESUME_RULES = ('Only real entries the owner provides; never invent employers, schools, dates or results. Months are '
                'optional (1-12); without them the Resume page shows years only. Leave the end year empty for '
                '"present". order is required: lower numbers show first.')

register(Resource(
    Experience,
    description='Jobs on the Resume page: role, organization, period and points (one achievement per line, no '
                'bullet characters). ' + RESUME_RULES,
    fields=['role', 'organization', 'start_year', 'start_month', 'end_year', 'end_month', 'points', 'order'],
    list_fields=['id', 'role', 'organization', 'start_year', 'end_year', 'order'],
    create=True,
))

register(Resource(
    Education,
    description='Education on the Resume page: title, school, an optional details line (e.g. a grade) and period. '
                + RESUME_RULES,
    fields=['title', 'organization', 'details', 'start_year', 'start_month', 'end_year', 'end_month', 'order'],
    list_fields=['id', 'title', 'organization', 'start_year', 'end_year', 'order'],
    create=True,
))

register(Resource(
    Image,
    name='images',
    singular='image',
    description='The image library: images placed in posts, projects and the About text with the Markdown in each '
                'image\'s "markdown" value. Photos are converted to WebP and resized when uploaded. Alt text says what '
                'the image shows, plainly, for screen readers and search engines.',
    fields=['alt'],
    read_only=['width', 'height', 'created_at'],
    computed={'markdown': lambda image: image.markdown},
    list_fields=['id', 'alt', 'file', 'created_at'],
    search=lambda images, text: images.filter(alt__icontains=text),
    create=True,
    uploads={'file': Upload(accept=['image/'], max_bytes=MAX_UPLOAD_BYTES)},
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
