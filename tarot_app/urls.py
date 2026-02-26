from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('tarot/', views.tarot, name='tarot'),
    path('runes/', views.runes, name='runes'),
    path('moon-calendar/', views.moon_calendar, name='moon_calendar'),
    path('human-design/', views.human_design, name='human_design'),
    path('about/', views.about, name='about'),
    path('contacts/', views.contacts, name='contacts'),
]