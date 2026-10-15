"""Clean uploaded SVG diagrams so they can be placed inline in pages.

Allowlist only: drawing elements and presentation attributes are kept; scripts, event handlers, embedded HTML,
<style>, external references and anything unknown are dropped. Files with a DOCTYPE or entities are rejected,
which blocks entity-expansion and external-entity attacks.
"""

import re
import xml.etree.ElementTree as ET

from django.core.exceptions import ValidationError

SVG_NS = 'http://www.w3.org/2000/svg'
XLINK_NS = 'http://www.w3.org/1999/xlink'

ELEMENTS = {
    'svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'text', 'tspan',
    'title', 'desc', 'defs', 'marker', 'use', 'clipPath', 'symbol',
}
ATTRIBUTES = {
    'viewBox', 'preserveAspectRatio', 'class', 'id', 'transform', 'd', 'x', 'y', 'x1', 'y1', 'x2', 'y2',
    'width', 'height', 'rx', 'ry', 'cx', 'cy', 'r', 'points', 'dx', 'dy',
    'fill', 'fill-opacity', 'fill-rule', 'stroke', 'stroke-width', 'stroke-opacity', 'stroke-dasharray',
    'stroke-linecap', 'stroke-linejoin', 'opacity', 'font-size', 'font-weight', 'font-family', 'text-anchor',
    'dominant-baseline', 'letter-spacing', 'marker-start', 'marker-mid', 'marker-end', 'markerWidth',
    'markerHeight', 'refX', 'refY', 'orient', 'markerUnits', 'clip-path', 'href',
    'data-name', 'data-info',
}
URL_ATTRIBUTES = {'marker-start', 'marker-mid', 'marker-end', 'clip-path', 'fill', 'stroke'}
LOCAL_URL = re.compile(r'^url\(#[\w.-]+\)$')
LOCAL_HREF = re.compile(r'^#[\w.-]+$')
MAX_BYTES = 512 * 1024


def _local(name):
    return name.split('}', 1)[-1]


def clean_svg(raw):
    """Return safe SVG markup for inline use, or raise ValidationError."""
    if len(raw) > MAX_BYTES:
        raise ValidationError('The SVG must be 512 KB or smaller.')
    text = raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else raw
    if re.search(r'<!DOCTYPE|<!ENTITY', text, re.I):
        raise ValidationError('SVG files with a DOCTYPE or entities are not allowed.')
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        raise ValidationError('This is not a valid SVG file.')
    if _local(root.tag) != 'svg':
        raise ValidationError('This is not an SVG file.')

    def scrub(element):
        for child in list(element):
            if not isinstance(child.tag, str) or _local(child.tag) not in ELEMENTS:
                element.remove(child)
            else:
                scrub(child)
        for name in list(element.attrib):
            local, value = _local(name), element.attrib[name].strip()
            if local not in ATTRIBUTES:
                del element.attrib[name]
            elif local == 'href':
                del element.attrib[name]
                if LOCAL_HREF.match(value):
                    element.set('href', value)
            elif local in URL_ATTRIBUTES and 'url(' in value and not LOCAL_URL.match(value):
                del element.attrib[name]
            elif 'javascript:' in value.lower() or 'expression(' in value.lower():
                del element.attrib[name]

    scrub(root)
    # sized by CSS, not by the file
    for name in ('width', 'height'):
        root.attrib.pop(name, None)
    root.set('class', ('diagram ' + root.get('class', '')).strip())
    root.set('aria-hidden', 'true')
    root.set('focusable', 'false')
    ET.register_namespace('', SVG_NS)
    return ET.tostring(root, encoding='unicode')
