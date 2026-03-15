from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
import json
from .models import TarotCard, TarotSpread


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


def tarot_view(request):
    """Основная view для страницы Таро"""
    cards = TarotCard.objects.all()
    total_cards = cards.count()

    context = {
        'cards': cards,
        'total_cards': total_cards,
    }
    return render(request, 'tarot.html', context)


@login_required
def get_spreads(request):
    """API для получения всех раскладов пользователя"""
    spreads = TarotSpread.objects.filter(user=request.user).order_by('-created_at')
    spreads_data = [spread.to_dict() for spread in spreads]
    return JsonResponse(spreads_data, safe=False)


@login_required
@require_http_methods(["POST"])
def save_spread(request):
    """API для сохранения нового расклада"""
    try:
        data = json.loads(request.body)

        spread_type = data.get('spread_type')
        question = data.get('question', '')
        cards = data.get('cards', [])

        if not spread_type or not cards:
            return JsonResponse({
                'success': False,
                'error': 'Не указан тип расклада или карты'
            }, status=400)

        # Создаем расклад
        spread = TarotSpread.objects.create(
            user=request.user,
            spread_type=spread_type,
            question=question,
            cards_data={'cards': cards}
        )

        return JsonResponse({
            'success': True,
            'spread': spread.to_dict()
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Неверный формат данных'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_spread(request, spread_id):
    """API для удаления расклада"""
    try:
        spread = get_object_or_404(TarotSpread, id=spread_id, user=request.user)
        spread.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_spread_detail(request, spread_id):
    """API для получения деталей конкретного расклада"""
    try:
        spread = get_object_or_404(TarotSpread, id=spread_id, user=request.user)
        return JsonResponse(spread.to_dict())
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def toggle_favorite(request, spread_id):
    """API для добавления/удаления из избранного"""
    try:
        spread = get_object_or_404(TarotSpread, id=spread_id, user=request.user)
        spread.is_favorite = not spread.is_favorite
        spread.save()
        return JsonResponse({
            'success': True,
            'is_favorite': spread.is_favorite
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def update_spread_note(request, spread_id):
    """API для обновления заметки расклада"""
    try:
        data = json.loads(request.body)
        note = data.get('note', '')

        spread = get_object_or_404(TarotSpread, id=spread_id, user=request.user)
        spread.note = note
        spread.save()

        return JsonResponse({
            'success': True,
            'note': spread.note
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


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
