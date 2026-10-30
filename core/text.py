import math

import markdown
from django.conf import settings
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


class ImageAttributes(Treeprocessor):
    """Images load lazily; library images get their width and height so the page doesn't jump as they load."""

    def run(self, root):
        images = list(root.iter('img'))
        if not images:
            return
        def name(img):
            return img.get('src', '').removeprefix(settings.MEDIA_URL)

        from .models import Image  # the models import this module
        library = Image.objects.filter(file__in={name(img) for img in images}, width__isnull=False)
        sizes = {image.file.name: (image.width, image.height) for image in library.only('file', 'width', 'height')}
        for img in images:
            img.set('loading', 'lazy')
            img.set('decoding', 'async')
            if size := sizes.get(name(img)):
                img.set('width', str(size[0]))
                img.set('height', str(size[1]))


class ImageExtension(Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(ImageAttributes(md), 'image_attributes', 5)


EXTENSIONS = ['fenced_code', 'codehilite', 'tables', 'sane_lists', 'smarty', ImageExtension()]
# startinline: PHP snippets are highlighted without an opening <?php tag
CONFIG = {'codehilite': {'css_class': 'highlight', 'guess_lang': False, 'startinline': True}}
WORDS_PER_MINUTE = 220


def render_markdown(text):
    """Markdown from admin to HTML. Code blocks use Pygments classes styled in pages.css."""
    if not text:
        return ''
    return markdown.markdown(text, extensions=EXTENSIONS, extension_configs=CONFIG, output_format='html')


def render_article(text):
    """(html, toc, minutes) for a blog post: headings get anchors, h2/h3 form the on-this-page list."""
    if not text:
        return '', [], 1
    md = markdown.Markdown(
        extensions=EXTENSIONS + ['toc'],
        extension_configs={**CONFIG, 'toc': {'toc_depth': '2-3', 'permalink': False}},
        output_format='html',
    )
    html = md.convert(text)
    toc = []
    for token in md.toc_tokens:  # nested h2 > h3
        toc.append({'id': token['id'], 'name': token['name'], 'level': 2})
        toc.extend({'id': child['id'], 'name': child['name'], 'level': 3} for child in token['children'])
    minutes = max(1, math.ceil(len(text.split()) / WORDS_PER_MINUTE))
    return html, toc, minutes
