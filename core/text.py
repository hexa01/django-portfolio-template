import math

import markdown

EXTENSIONS = ['fenced_code', 'codehilite', 'tables', 'sane_lists', 'smarty']
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
