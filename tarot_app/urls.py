from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('tarot/', views.tarot, name='tarot'),
    path('runes/', views.runes, name='runes'),
    path('moon-calendar/', views.moon_calendar, name='moon_calendar'),
    path('human-design/', views.human_design, name='human_design'),
    path('about/', views.about, name='about'),
    path('contacts/', views.contacts, name='contacts'),

    # API endpoints - убедитесь, что они не конфликтуют с основными маршрутами
    path('api/spreads/', views.get_spreads, name='get-spreads'),
    path('api/spreads/save/', views.save_spread, name='save-spread'),
    path('api/spreads/<int:spread_id>/', views.get_spread_detail, name='spread-detail'),
    path('api/spreads/<int:spread_id>/delete/', views.delete_spread, name='delete-spread'),
    path('api/spreads/<int:spread_id>/favorite/', views.toggle_favorite, name='toggle-favorite'),
    path('api/spreads/<int:spread_id>/note/', views.update_spread_note, name='update-note'),

    # Новый эндпоинт для нейросети
    path('api/ai-interpret/', views.get_ai_interpretation, name='ai-interpret'),
]

# Добавляем поддержку media файлов только в режиме DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
