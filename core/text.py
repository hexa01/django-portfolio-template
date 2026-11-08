import math
import re
from html import unescape
from xml.etree import ElementTree as etree

import markdown
from django.conf import settings
from django.urls import reverse
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


class ImageAttributes(Treeprocessor):
    """Images load lazily; library images get their width and height so the page doesn't jump as they load.
    With eager_first, the first image loads right away: in an article it's usually on screen at once, and a lazy
    first image makes the browser wait before fetching it."""

    def __init__(self, md, eager_first=False):
        super().__init__(md)
        self.eager_first = eager_first

    def run(self, root):
        images = list(root.iter('img'))
        if not images:
            return
        def name(img):
            return img.get('src', '').removeprefix(settings.MEDIA_URL)

        from .models import Image  # the models import this module
        library = Image.objects.filter(file__in={name(img) for img in images}, width__isnull=False)
        sizes = {image.file.name: (image.width, image.height) for image in library.only('file', 'width', 'height')}
        for position, img in enumerate(images):
            if position or not self.eager_first:
                img.set('loading', 'lazy')
            img.set('decoding', 'async')
            if size := sizes.get(name(img)):
                img.set('width', str(size[0]))
                img.set('height', str(size[1]))


class ImageExtension(Extension):
    def __init__(self, eager_first=False):
        super().__init__()
        self.eager_first = eager_first

    def extendMarkdown(self, md):
        md.treeprocessors.register(ImageAttributes(md, self.eager_first), 'image_attributes', 5)


def _table_as_list(table):
    """A table as a bulleted list, one item per row, for platforms without tables."""
    (_, *headers), *rows = [[''.join(cell.itertext()).strip() for cell in row] for row in table.iter('tr')]
    items = etree.Element('ul')
    for first, *cells in rows:
        item = etree.SubElement(items, 'li')
        etree.SubElement(item, 'strong').text = first
        item[0].tail = ': ' + '. '.join(f'{header}: {cell}' for header, cell in zip(headers, cells)) + '.'
    return items


class ImportCleanup(Treeprocessor):
    """Rewrites what Medium's importer drops: tables become lists, library WebP images point at their PNG version."""

    def run(self, root):
        for parent in list(root.iter()):
            for position, child in enumerate(list(parent)):
                if child.tag == 'table':
                    parent.remove(child)
                    parent.insert(position, _table_as_list(child))
        from .models import Image  # the models import this module
        images = list(root.iter('img'))
        names = {img.get('src', '').removeprefix(settings.MEDIA_URL) for img in images}
        library = {image.file.name: image.pk for image in Image.objects.filter(file__in=names, file__endswith='.webp')}
        for img in images:
            if pk := library.get(img.get('src', '').removeprefix(settings.MEDIA_URL)):
                img.set('src', reverse('blog:image-png', args=[pk]))


class ImportExtension(Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(ImportCleanup(md), 'import_cleanup', 5)


BASE_EXTENSIONS = ['fenced_code', 'codehilite', 'tables', 'sane_lists', 'smarty']
EXTENSIONS = BASE_EXTENSIONS + [ImageExtension()]
ARTICLE_EXTENSIONS = BASE_EXTENSIONS + [ImageExtension(eager_first=True), 'toc']
# startinline: PHP snippets are highlighted without an opening <?php tag
CONFIG = {'codehilite': {'css_class': 'highlight', 'guess_lang': False, 'startinline': True}}
WORDS_PER_MINUTE = 220


def render_markdown(text):
    """Markdown from admin to HTML. Code blocks use Pygments classes styled in pages.css."""
    if not text:
        return ''
    return markdown.markdown(text, extensions=EXTENSIONS, extension_configs=CONFIG, output_format='html')


def render_for_import(text):
    """HTML that survives Medium's importer: code without highlighting tags, no tables, PNG instead of WebP."""
    extensions = ['fenced_code', 'tables', 'sane_lists', 'smarty', ImportExtension()]
    html = markdown.markdown(text, extensions=extensions, output_format='html')
    return re.sub(r'<code class="language-[^"]*">', '<code>', html)


def render_article(text):
    """(html, toc, minutes) for a blog post: headings get anchors, h2/h3 form the on-this-page list."""
    if not text:
        return '', [], 1
    md = markdown.Markdown(
        extensions=ARTICLE_EXTENSIONS,
        extension_configs={**CONFIG, 'toc': {'toc_depth': '2-3', 'permalink': False}},
        output_format='html',
    )
    html = md.convert(text)
    toc = []
    for token in md.toc_tokens:  # nested h2 > h3
        # token names hold HTML entities (a smartened apostrophe is &rsquo;); the template escapes them again
        toc.append({'id': token['id'], 'name': unescape(token['name']), 'level': 2})
        toc.extend({'id': child['id'], 'name': unescape(child['name']), 'level': 3} for child in token['children'])
    minutes = max(1, math.ceil(len(text.split()) / WORDS_PER_MINUTE))
    return html, toc, minutes
