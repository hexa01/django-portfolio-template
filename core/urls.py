from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('resume/', views.ResumeView.as_view(), name='resume'),
    path('search/', views.search, name='search'),
    path('health/', views.health, name='health'),
    path('favicon.svg', views.favicon, name='favicon'),
    path('og/site.png', views.og_site, name='og-site'),
    path('og/projects/<slug:slug>.png', views.og_project, name='og-project'),
    path('og/posts/<slug:slug>.png', views.og_post, name='og-post'),
    path(
        'robots.txt',
        TemplateView.as_view(template_name='robots.txt', content_type='text/plain'),
        name='robots',
    ),
]
