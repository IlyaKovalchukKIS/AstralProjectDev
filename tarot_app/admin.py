from django.contrib import admin
from .models import TarotCard, Rune, HumanDesign, TarotSpread


@admin.register(TarotCard)
class TarotCardAdmin(admin.ModelAdmin):
    list_display = ['name', 'arcana_type', 'number', 'image']
    list_filter = ['arcana_type']
    search_fields = ['name']
    # list_editable = ['number']


@admin.register(TarotSpread)
class TarotSpreadAdmin(admin.ModelAdmin):
    list_display = ['user', 'spread_type', 'question', 'created_at']
    list_filter = ['user']
    search_fields = ['user']
    # list_editable = ['number']


@admin.register(Rune)
class RuneAdmin(admin.ModelAdmin):
    """Админка для рун"""
    list_display = ('id', 'name', 'symbol')
    search_fields = ('name',)


@admin.register(HumanDesign)
class HumanDesignAdmin(admin.ModelAdmin):
    """Админка для Human Design профилей"""
    list_display = ('id', 'created_at', 'profile_data_summary')
    readonly_fields = ('created_at',)  # дата создания только для чтения

    def profile_data_summary(self, obj):
        """Краткое представление JSON-данных"""
        import json
        data_str = json.dumps(obj.profile_data, ensure_ascii=False)
        return data_str[:50] + '…' if len(data_str) > 50 else data_str

    profile_data_summary.short_description = 'Данные профиля'
