from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from accounts.views import register, login_view, profile_view, logout_view, profile_edit, home
from news.views import news_detail, news_list, edit_news, delete_news, create_news

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('register/', register, name='register'),
    path('login/', login_view, name='login'),
    path('profile/', profile_view, name='profile'),
    path('logout/', logout_view, name='logout'),
    path('profile/profile_edit/', profile_edit, name='profile_edit'),
    path('news/', news_list, name='news_list'),
    path('news/<int:pk>/', news_detail, name='news_detail'),
    path('news/<int:pk>/edit/', edit_news, name='news_edit'),
    path('news/<int:pk>/delete/', delete_news, name='news_delete'),
    path('news/create/', create_news, name='create_news'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
