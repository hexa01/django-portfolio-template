from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Decision, Project

PLAIN_STATIC = override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
)


def make(slug='rag-service', **fields):
    defaults = dict(title='RAG service', summary='Answers questions.', year=2026, status=Project.Status.PUBLISHED)
    defaults.update(fields)
    return Project.objects.create(slug=slug, **defaults)


@PLAIN_STATIC
class ProjectTests(TestCase):
    def test_only_published_projects_are_listed_and_reachable(self):
        make('live-one', title='Live one')
        make('hidden-one', title='Hidden one', status=Project.Status.DRAFT)
        response = self.client.get(reverse('projects:index'))
        self.assertContains(response, 'Live one')
        self.assertNotContains(response, 'Hidden one')
        self.assertEqual(self.client.get(reverse('projects:detail', args=['hidden-one'])).status_code, 404)
        self.assertEqual(self.client.get(reverse('projects:detail', args=['no-such'])).status_code, 404)

    def test_markdown_is_rendered_on_save(self):
        project = make(problem='Search **missed** paraphrases.')
        self.assertEqual(project.problem_html, '<p>Search <strong>missed</strong> paraphrases.</p>')
        response = self.client.get(project.get_absolute_url())
        self.assertContains(response, '<h2 id="problem">Problem</h2>', html=True)
        self.assertNotContains(response, '<h2 id="result">Result</h2>', html=True)  # empty sections stay hidden

    def test_detail_shows_decisions_stack_and_active_nav(self):
        project = make(stack='Python, pgvector , ')
        Decision.objects.create(project=project, decision='pgvector over a vector DB', why='Filters in one query', tradeoff='Lower scale ceiling')
        self.assertEqual(project.stack_list, ['Python', 'pgvector'])
        response = self.client.get(project.get_absolute_url())
        self.assertContains(response, '<h3>pgvector over a vector DB</h3>', html=True)
        self.assertContains(response, '<dd>Lower scale ceiling</dd>', html=True)
        self.assertContains(response, '<li>pgvector</li>', html=True)
        self.assertContains(response, f'<a href="{reverse("projects:index")}" aria-current="page">Projects<span class="nav-mark" aria-hidden="true"></span></a>', html=True)

    def test_links_only_when_set_otherwise_the_note(self):
        private = make('private-one', availability_note='Code private (client work)')
        response = self.client.get(private.get_absolute_url())
        self.assertContains(response, 'Code private (client work)')
        self.assertNotContains(response, 'Source code')
        self.assertNotContains(response, 'SoftwareSourceCode')
        public = make('public-one', source_url='https://github.com/example/repo')
        response = self.client.get(public.get_absolute_url())
        self.assertContains(response, 'href="https://github.com/example/repo"')
        # structured data ties the case study to its repository
        self.assertContains(response, '"codeRepository": "https://github.com/example/repo"')

    def test_home_shows_featured_projects_and_list_handles_empty(self):
        self.assertContains(self.client.get(reverse('projects:index')), 'Projects are being written up')
        make('plain-one', title='Plain one')
        make('star-one', title='Star one', featured=True)
        home = self.client.get(reverse('core:home'))
        self.assertContains(home, 'Star one')
        self.assertNotContains(home, 'Plain one')


HOSTILE_SVG = b'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="400" height="200"
  viewBox="0 0 400 200" onload="alert(1)">
  <script>alert(2)</script>
  <style>rect { fill: url(https://evil.example/x) }</style>
  <foreignObject><div xmlns="http://www.w3.org/1999/xhtml">html</div></foreignObject>
  <rect class="node hot" x="0" y="0" width="80" height="30" onclick="alert(3)" fill="url(https://evil.example/p)"/>
  <a href="javascript:alert(4)"><text x="5" y="20">click</text></a>
  <use xlink:href="https://evil.example/sprite.svg#icon"/>
  <use href="#local"/>
  <path class="edge" d="M80 15 H120" marker-end="url(#arrow)"/>
</svg>'''


class SvgCleaningTests(TestCase):
    def test_scripts_handlers_html_and_external_references_are_removed(self):
        from core.svg import clean_svg
        out = clean_svg(HOSTILE_SVG)
        for bad in ('script', 'onload', 'onclick', 'alert', 'foreignObject', '<style', 'evil.example', 'javascript', '<a '):
            self.assertNotIn(bad, out)
        self.assertIn('class="node hot"', out)          # drawing and classes kept
        self.assertIn('href="#local"', out)             # in-document references kept
        self.assertIn('marker-end="url(#arrow)"', out)
        self.assertNotIn('width="400"', out)            # sized by CSS
        self.assertIn('class="diagram"', out)

    def test_entities_and_non_svg_are_rejected(self):
        from django.core.exceptions import ValidationError
        from core.svg import clean_svg
        bomb = b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "aaaa">]><svg xmlns="http://www.w3.org/2000/svg">&a;</svg>'
        for bad in (bomb, b'<html><body>no</body></html>', b'not xml at all'):
            with self.assertRaises(ValidationError):
                clean_svg(bad)


@PLAIN_STATIC
class DiagramTests(TestCase):
    def setUp(self):
        import shutil
        import tempfile
        self.media = tempfile.mkdtemp()
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)

    def test_svg_diagram_is_cleaned_and_shown_inline(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        project = make(diagram=SimpleUploadedFile('flow.svg', HOSTILE_SVG, content_type='image/svg+xml'))
        self.assertNotIn('script', project.diagram_svg)
        response = self.client.get(project.get_absolute_url())
        self.assertContains(response, 'role="img" aria-label="Architecture of RAG service"')
        self.assertContains(response, '<rect class="node hot"')
        self.assertNotContains(response, 'alert(')

    def test_png_diagram_is_an_image_and_no_diagram_means_no_figure(self):
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        buffer = BytesIO()
        Image.new('RGB', (2400, 1500), (10, 20, 30)).save(buffer, format='PNG')
        project = make(diagram=SimpleUploadedFile('flow.png', buffer.getvalue(), content_type='image/png'))
        self.assertEqual(project.diagram_svg, '')
        with Image.open(project.diagram.path) as stored:
            self.assertEqual(stored.width, 1600)
        self.assertContains(self.client.get(project.get_absolute_url()), f'src="{project.diagram.url}"')
        plain = make('plain-one')
        self.assertNotContains(self.client.get(plain.get_absolute_url()), '<figure')


@override_settings(AGENT_CONTENT_REQUIRE_HTTPS=False)
class AgentResourceTests(TestCase):
    """This site's rules for agents (projects/agent_resources.py)."""

    def test_agents_edit_text_and_decisions_but_cannot_create_projects(self):
        import io
        import json
        from django.core.management import call_command
        out = io.StringIO()
        call_command('agent_content_key', '--user', 'bot', stdout=out)
        auth = {'HTTP_AUTHORIZATION': 'Bearer ' + next(l for l in out.getvalue().splitlines() if l.startswith('ac_'))}
        project = make()

        def send(method, path, data):
            return getattr(self.client, method)('/api/agent/' + path, json.dumps(data), content_type='application/json', **auth)

        self.assertEqual(send('post', 'projects/', {'title': 'New'}).status_code, 405)
        self.assertEqual(send('patch', f'projects/{project.slug}/', {'result': 'It **works**.'}).status_code, 200)
        project.refresh_from_db()
        self.assertEqual(project.result_html, '<p>It <strong>works</strong>.</p>')
        response = send('put', f'projects/{project.slug}/decisions/', {'items': [{'decision': 'A', 'why': 'B', 'tradeoff': 'C'}]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(project.decisions.values_list('decision', flat=True)), ['A'])
