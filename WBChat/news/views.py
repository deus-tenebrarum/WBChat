from django.shortcuts import render, get_object_or_404, redirect
from .models import News
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
@login_required(login_url='login')
def news_list(request):
    news = News.objects.order_by('-created_at')
    return render(request, 'news/news_list.html', {'news': news})
@login_required(login_url='login')
def news_detail(request, pk):
    news_item = get_object_or_404(News, pk=pk)
    return render(request, 'news/news_detail.html', {'news_item': news_item})
@login_required(login_url='login')
def edit_news(request, pk):
    news_item = get_object_or_404(News, pk=pk)

    if not request.user.is_authenticated or not request.user.isModerator:
        return HttpResponseForbidden("У вас нет прав.")

    if request.method == 'POST':
        news_item.title = request.POST.get('title')
        news_item.content = request.POST.get('content')

        if request.FILES.get('image'):
            news_item.image = request.FILES['image']

        news_item.save()
        return redirect('news_detail', pk=news_item.pk)

    return render(request, 'news/edit_news.html', {'news_item': news_item})
@login_required(login_url='login')
def delete_news(request, pk):
    news_item = get_object_or_404(News, pk=pk)

    if not request.user.is_authenticated or not request.user.isModerator:
        return HttpResponseForbidden("У вас нет прав.")

    news_item.delete()
    return redirect('news_list')
@login_required(login_url='login')
def create_news(request):
    if not request.user.is_authenticated or not request.user.isModerator:
        return HttpResponseForbidden("У вас нет прав.")

    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        image = request.FILES.get("image")

        News.objects.create(
            title=title,
            content=content,
            author=request.user,
            image=image
        )

        return redirect('news_list')

    return render(request, "news/create_news.html")
