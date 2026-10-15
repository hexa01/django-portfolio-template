from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from core import og, seo
from core.models import PageText, SiteProfile

from .models import Category, Post, Tag

PER_PAGE = 10


def index(request):
    posts = Post.objects.published().select_related('category')
    category = tag = None
    query = request.GET.get('q', '').strip()[:100]
    if slug := request.GET.get('category'):
        category = get_object_or_404(Category, slug=slug)
        posts = posts.filter(category=category)
    if slug := request.GET.get('tag'):
        tag = get_object_or_404(Tag, slug=slug)
        posts = posts.filter(tags=tag)
    if query:
        posts = posts.search(query)

    page = Paginator(posts, PER_PAGE).get_page(request.GET.get('page'))
    title = f'Posts tagged {tag}' if tag else category.name if category else 'Blog'
    text = PageText.context(PageText.Page.BLOG, SiteProfile.load())
    if category or tag:
        text['full_title'] = ''  # filtered lists keep their own title ("Posts tagged …")
    return render(request, 'blog/index.html', {
        'meta_title': title, 'heading': 'Blog', **text,
        'page': page, 'posts': page.object_list,
        'categories': Category.objects.filter(posts__in=Post.objects.published()).distinct(),
        'category': category, 'tag': tag, 'query': query,
        'filtered': bool(category or tag or query),
        # filtered and searched lists are not separate pages for search engines
        'noindex': bool(tag or query or page.number > 1),
    })


def detail(request, slug):
    # staff can open drafts and scheduled posts to review them before publishing
    visible = Post.objects.all() if request.user.is_staff else Post.objects.published()
    post = get_object_or_404(visible.select_related('category'), slug=slug)
    published = Post.objects.published()
    preview = post not in published
    if post.cover:
        image = request.build_absolute_uri(post.cover.url)
    else:
        image = og.url(request, 'core:og-post', post.slug, post.title)
    return render(request, 'blog/detail.html', {
        'meta_title': post.seo_title or post.title,
        'meta_description': post.seo_description or post.excerpt,
        'og_type': 'article',
        'og_image': image,
        'og_image_custom': bool(post.cover),
        'share_url': request.build_absolute_uri(post.get_absolute_url()),
        'schema': [
            seo.article(request, post, SiteProfile.load(), image),
            seo.breadcrumbs(request, ('Home', reverse('core:home')), ('Blog', reverse('blog:index')),
                            (post.title, post.get_absolute_url())),
        ],
        'post': post,
        'tags': post.tags.all(),
        'preview': preview,
        'noindex': preview,
        'newer': None if preview else published.filter(published_at__gt=post.published_at).order_by('published_at').first(),
        'older': None if preview else published.filter(published_at__lt=post.published_at).order_by('-published_at').first(),
    })
