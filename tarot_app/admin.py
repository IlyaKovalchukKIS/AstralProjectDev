from django.contrib import admin
from .models import TarotCard

@admin.register(TarotCard)
class TarotCardAdmin(admin.ModelAdmin):
    list_display = ['name', 'arcana_type', 'number']
    list_filter = ['arcana_type']
    search_fields = ['name']
    list_editable = ['number']
