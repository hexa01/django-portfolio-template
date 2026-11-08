import shutil
import tempfile
from datetime import timedelta
from io import BytesIO

from PIL import Image as PILImage

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Image as LibraryImage

from .models import Category, Post, Tag

PLAIN_STATIC = override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
)

BODY = '''Intro.

## Why cache

Text about **caching**.

### Exact match

```python
def get(key):
    return cache[key]
```

## Trade-offs

Done.
'''


def make(slug='semantic-cache', days_ago=1, **fields):
    defaults = dict(
        title='Semantic caching', excerpt='How a two-layer cache cuts LLM calls.', body=BODY,
        status=Post.Status.PUBLISHED, published_at=timezone.now() - timedelta(days=days_ago),
    )
    defaults.update(fields)
    return Post.objects.create(slug=slug, **defaults)


@PLAIN_STATIC
class PostTests(TestCase):
    def test_markdown_toc_and_reading_time_are_stored_on_save(self):
        post = make()
        self.assertIn('<h2 id="why-cache">Why cache</h2>', post.body_html)
        self.assertIn('class="highlight"', post.body_html)
        self.assertEqual([(t['id'], t['level']) for t in post.toc], [('why-cache', 2), ('exact-match', 3), ('trade-offs', 2)])
        self.assertEqual(post.reading_minutes, 1)

    def test_publishing_sets_the_date_and_drafts_and_future_posts_stay_hidden(self):
        draft = make('draft-one', status=Post.Status.DRAFT, published_at=None)
        self.assertIsNone(draft.published_at)
        draft.status = Post.Status.PUBLISHED
        draft.save()
        self.assertIsNotNone(draft.published_at)

        make('hidden-one', title='Hidden one', status=Post.Status.DRAFT)
        make('later-one', title='Later one', days_ago=-3)
        response = self.client.get(reverse('blog:index'))
        self.assertNotContains(response, 'Hidden one')
        self.assertNotContains(response, 'Later one')
        for slug in ('hidden-one', 'later-one', 'no-such'):
            self.assertEqual(self.client.get(reverse('blog:detail', args=[slug])).status_code, 404)

    def test_detail_page_has_toc_tags_article_meta_and_neighbours(self):
        older = make('older-one', title='Older one', days_ago=5)
        post = make()
        post.tags.add(Tag.objects.create(name='RAG', slug='rag'))
        response = self.client.get(post.get_absolute_url())
        self.assertContains(response, '<a href="#exact-match">Exact match</a>', html=True)
        self.assertContains(response, 'href="/blog/?tag=rag"')
        self.assertContains(response, '<meta property="og:type" content="article">', html=True)
        self.assertContains(response, 'article:published_time')
        self.assertContains(response, older.get_absolute_url())
        self.assertContains(response, f'<link rel="canonical" href="http://testserver{post.get_absolute_url()}">', html=True)

    def test_cross_posted_article_points_canonical_to_the_original(self):
        post = make(canonical_url='https://medium.com/@someone/a-post-123')
        response = self.client.get(post.get_absolute_url())
        self.assertContains(response, '<link rel="canonical" href="https://medium.com/@someone/a-post-123">', html=True)
        self.assertContains(response, 'First published on')
        self.assertEqual(post.origin_name, 'Medium')

    def test_category_tag_and_search_filter_the_list(self):
        notes = Category.objects.create(name='Notes', slug='notes')
        rag = Tag.objects.create(name='RAG', slug='rag')
        caching = make(category=notes)
        caching.tags.add(rag)
        make('agents', title='Building agents', excerpt='Tools and graphs for an LLM agent.', body='LangGraph state machines.')

        by_category = self.client.get(reverse('blog:index'), {'category': 'notes'})
        self.assertContains(by_category, 'Semantic caching')
        self.assertNotContains(by_category, 'Building agents')
        self.assertNotContains(self.client.get(reverse('blog:index'), {'tag': 'rag'}), 'Building agents')
        self.assertEqual(self.client.get(reverse('blog:index'), {'tag': 'nope'}).status_code, 404)

        search = self.client.get(reverse('blog:index'), {'q': 'langgraph'})
        self.assertContains(search, 'Building agents')
        self.assertNotContains(search, 'Semantic caching')
        self.assertContains(search, 'name="robots" content="noindex, follow"')
        self.assertContains(self.client.get(reverse('blog:index'), {'q': 'zzzz'}), 'No posts match')

    def test_list_paginates_and_home_shows_latest_three(self):
        for i in range(12):
            make(f'post-{i}', title=f'Post number {i}', days_ago=i + 1)
        first = self.client.get(reverse('blog:index'))
        self.assertContains(first, 'Post number 0')
        self.assertNotContains(first, 'Post number 11')
        self.assertContains(first, 'rel="next"')
        self.assertContains(self.client.get(reverse('blog:index'), {'page': 2}), 'Post number 11')
        home = self.client.get(reverse('core:home'))
        self.assertContains(home, 'Latest writing')
        self.assertContains(home, 'Post number 2')
        self.assertNotContains(home, 'Post number 3')

    def test_checklist_is_advisory(self):
        post = make(excerpt='Short.', body='![](x.png)')
        failed = [label for label, ok in post.checklist() if not ok]
        self.assertIn('Excerpt is 50 to 160 characters', failed)
        self.assertIn('Every image in the body has a description', failed)
        self.assertEqual(Post.objects.published().filter(pk=post.pk).count(), 1)  # still saved and published


@PLAIN_STATIC
class PreviewTests(TestCase):
    def test_staff_can_preview_drafts_and_visitors_cannot(self):
        from django.contrib.auth.models import User
        draft = make('draft-one', status=Post.Status.DRAFT, published_at=None)
        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 404)
        self.client.force_login(User.objects.create_user('editor', is_staff=True))
        response = self.client.get(draft.get_absolute_url())
        self.assertContains(response, 'only visible to staff')
        self.assertContains(response, 'name="robots" content="noindex, follow"')


@PLAIN_STATIC
@override_settings(AGENT_CONTENT_REQUIRE_HTTPS=False)
class AgentResourceTests(TestCase):
    """This site's rules for agents (blog/agent_resources.py); the API itself is tested in django-agent-content."""

    def setUp(self):
        import io
        from django.core.management import call_command
        out = io.StringIO()
        call_command('agent_content_key', '--user', 'bot', stdout=out)
        self.auth = {'HTTP_AUTHORIZATION': 'Bearer ' + next(l for l in out.getvalue().splitlines() if l.startswith('ac_'))}

    def send(self, method, path, data):
        import json
        response = getattr(self.client, method)('/api/agent/' + path, json.dumps(data), content_type='application/json', **self.auth)
        return response.status_code, response.json()

    def test_new_posts_are_drafts_and_publish_sets_the_date(self):
        status, post = self.send('post', 'posts/', {'title': 'Agent post', 'slug': 'agent-post',
                                                   'excerpt': 'Written through the API.', 'body': '## One\n\nText.'})
        self.assertEqual((status, post['status'], post['url']), (201, 'draft', '/blog/agent-post/'))
        self.assertEqual(self.client.get('/blog/agent-post/').status_code, 404)  # not public yet
        status, post = self.send('post', 'posts/agent-post/publish/', {'published_at': '2026-04-08T09:00:00+00:00'})
        self.assertEqual((status, post['status']), (200, 'published'))
        self.assertContains(self.client.get('/blog/agent-post/'), '8 April 2026')

    def test_published_slug_is_locked(self):
        make('live')
        status, body = self.send('patch', 'posts/live/', {'slug': 'moved'})
        self.assertEqual(status, 400)
        self.assertIn('slug', body['error'])


@PLAIN_STATIC
class MediumImportTests(TestCase):
    """Medium's importer identifies as Embedly and drops highlighted code, WebP images and tables."""

    EMBEDLY = {'HTTP_USER_AGENT': 'Mozilla/5.0 (compatible; Embedly/0.2; +http://support.embed.ly/)'}

    def setUp(self):
        self.media = tempfile.mkdtemp()
        override = override_settings(MEDIA_ROOT=self.media)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        buffer = BytesIO()
        PILImage.new('RGB', (300, 200), (10, 20, 30)).save(buffer, format='PNG')
        self.image = LibraryImage(file=SimpleUploadedFile('flow.png', buffer.getvalue()), alt='A flow')
        self.image.save()

    def post(self, **fields):
        body = ('Intro.\n\n' + self.image.markdown + '\n\n```python\ndef get(key):\n    return key\n```\n\n'
                '| Time | Tokens |\n|---|---|\n| 0 s | 20 |\n| 1 s | 5 |\n')
        return Post.objects.create(**{'title': 'Buckets', 'slug': 'buckets', 'excerpt': 'About buckets.', 'body': body,
                                      'status': Post.Status.PUBLISHED, 'published_at': timezone.now(), **fields})

    def test_visitors_get_the_normal_page_and_the_importer_the_plain_one(self):
        url = self.post().get_absolute_url()
        normal = self.client.get(url)
        self.assertContains(normal, 'class="highlight"')
        self.assertContains(normal, '.webp')
        self.assertIn('User-Agent', normal['Vary'])

        plain = self.client.get(url, **self.EMBEDLY)
        self.assertContains(plain, '<title>Buckets</title>', html=True)
        self.assertContains(plain, '<pre><code>def get(key):')
        self.assertNotContains(plain, 'highlight')
        self.assertNotContains(plain, '.webp')
        self.assertNotContains(plain, '<table')
        self.assertContains(plain, '<li><strong>0 s</strong>: Tokens: 20.</li>', html=True)
        self.assertContains(plain, f'rel="canonical" href="http://testserver{url}"')
        self.assertContains(plain, reverse('blog:image-png', args=[self.image.pk]))

    def test_library_images_are_served_as_png(self):
        response = self.client.get(reverse('blog:image-png', args=[self.image.pk]))
        self.assertEqual(response['Content-Type'], 'image/png')
        with PILImage.open(BytesIO(response.content)) as png:
            self.assertEqual((png.format, png.size), ('PNG', (300, 200)))
        self.assertEqual(self.client.get(reverse('blog:image-png', args=[999])).status_code, 404)

    def test_drafts_stay_hidden_and_cross_posts_stay_normal(self):
        draft = self.post(status=Post.Status.DRAFT, published_at=None)
        self.assertEqual(self.client.get(draft.get_absolute_url(), **self.EMBEDLY).status_code, 404)
        draft.delete()
        cross = self.post(canonical_url='https://medium.com/@someone/buckets-123')
        self.assertContains(self.client.get(cross.get_absolute_url(), **self.EMBEDLY), 'class="highlight"')

