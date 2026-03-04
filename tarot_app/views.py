from django.shortcuts import render
from .models import TarotCard
import random


def home(request):
    return render(request, 'home.html')


def tarot(request):
    """
    Отображает страницу с раскладами Таро
    Передает все карты в шаблон для дальнейшей обработки JavaScript
    """
    # Получаем все карты из базы данных
    cards = TarotCard.objects.all()

    context = {
        'cards': cards,  # Передаем все карты для JS
        'total_cards': cards.count(),
    }

    return render(request, 'tarot.html', context)


def runes(request):
    return render(request, 'runes.html')


def moon_calendar(request):
    return render(request, 'moon_calendar.html')


def human_design(request):
    return render(request, 'human_design.html')


def about(request):
    return render(request, 'about.html')


def contacts(request):
    return render(request, 'contacts.html')