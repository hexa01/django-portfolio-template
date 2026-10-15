"""What AI agents may edit in the blog (through agent_content's API)."""

from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime

from agent_content import Action, Relation, Resource, register, slug_defaults

from .models import Category, Post, Tag


def publish(post, data):
    """The "publish" action: make a post public, optionally with the date to show."""
    when = data.get('published_at')
    published_at = parse_datetime(when) if when else None
    if when and published_at is None:
        raise ValidationError('published_at must be an ISO date, e.g. 2026-04-08T09:00:00+05:45.')
    post.status = Post.Status.PUBLISHED
    if published_at:
        post.published_at = published_at
    post.save()  # save() sets published_at to now when it is still empty
    return post


register(Resource(
    Post,
    description='Blog posts: technical articles in Markdown. Use ## and ### for sections (never #) and give code '
                'fences a language. Never invent results, numbers or claims; ask the owner when content is missing.',
    lookup='slug',
    fields=['title', 'slug', 'excerpt', 'body', 'category', 'tags', 'seo_title', 'seo_description',
            'canonical_url', 'updated_at'],
    read_only=['status', 'published_at', 'reading_minutes'],
    computed={
        'url': lambda post: post.get_absolute_url(),
        'checklist_failing': lambda post: [label for label, ok in post.checklist() if not ok],
    },
    list_fields=['slug', 'title', 'status', 'published_at', 'category'],
    relations={'category': Relation('name'), 'tags': Relation('name', create=True, create_defaults=slug_defaults)},
    create=True,
    defaults={'status': Post.Status.DRAFT},
    locked_fields=['slug'],
    locked_if=lambda post: post.status == Post.Status.PUBLISHED,
    filters=['status'],
    search=lambda posts, text: posts.search(text),
    actions={'publish': Action(publish, 'Make the post public. Only when the owner asks to publish it.',
                               {'published_at': 'ISO date to show on the post, e.g. when it was written; optional, default now'})},
))
