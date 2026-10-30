"""What AI agents may edit in projects (through agent_content's API). Creating projects stays in admin."""

from agent_content import Inline, Resource, Upload, register

from core.media import MAX_UPLOAD_BYTES

from .models import Decision, Project

register(Resource(
    Project,
    description='Portfolio projects (case studies). problem, approach and result are Markdown under the page\'s own '
                'section headings, so use ### inside them. Results are real outcomes only, never invented numbers.',
    lookup='slug',
    fields=['title', 'summary', 'role', 'stack', 'problem', 'approach', 'result', 'diagram_caption'],
    read_only=['status', 'year', 'featured'],
    computed={'url': lambda project: project.get_absolute_url()},
    list_fields=['slug', 'title', 'status', 'year', 'featured'],
    inlines={'decisions': Inline(Decision, fk='project', fields=['decision', 'why', 'tradeoff'], order_field='order')},
    uploads={'diagram': Upload(accept=['image/'], max_bytes=MAX_UPLOAD_BYTES)},
))
