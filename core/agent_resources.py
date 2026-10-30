"""What AI agents may edit in core: the site profile, the fixed pages' texts and the image library
(through agent_content's API)."""

from agent_content import Resource, Upload, register

from .media import MAX_UPLOAD_BYTES
from .models import Image, PageText, SiteProfile

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
