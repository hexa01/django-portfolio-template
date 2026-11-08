from django.urls import path

from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.index, name='index'),
    path('images/<int:pk>.png', views.image_png, name='image-png'),
    path('<slug:slug>/', views.detail, name='detail'),
]
