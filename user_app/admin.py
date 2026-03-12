from django.contrib import admin
from .models import (
    User, SubscriptionPlan, ExtensionOption,
    UserSubscription, ExtensionHistory, Payment, Privilege
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_active', 'is_staff')
    ordering = ('-date_joined',)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'is_popular', 'order', 'privileges_count')
    list_editable = ('price', 'duration_days', 'is_popular', 'order')
    search_fields = ('name', 'description')
    list_filter = ('is_popular',)
    ordering = ('order', 'price')
    filter_horizontal = ('privileges',)  # Удобный виджет для выбора привилегий

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'price', 'duration_days', 'description')
        }),
        ('Привилегии', {
            'fields': ('privileges',),
            'description': 'Выберите привилегии, которые будут доступны в этом тарифе'
        }),
        ('Настройки отображения', {
            'fields': ('is_popular', 'order', 'color', 'icon')
        }),
    )

    def privileges_count(self, obj):
        """Возвращает количество привилегий в тарифе"""
        count = obj.privileges.count()
        return f"{count} привилегий" if count else "Нет"

    privileges_count.short_description = 'Привилегии'


@admin.register(ExtensionOption)
class ExtensionOptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'months', 'days', 'discount_percent', 'is_active', 'is_popular', 'order')
    list_editable = ('days', 'discount_percent', 'is_active', 'is_popular', 'order')
    search_fields = ('name', 'description')
    list_filter = ('is_active', 'is_popular')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'icon')
        }),
        ('Параметры', {
            'fields': ('months', 'days', 'discount_percent')
        }),
        ('Настройки отображения', {
            'fields': ('is_active', 'is_popular', 'order')
        }),
    )


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active', 'extended_count')
    list_filter = ('is_active', 'plan', 'start_date')
    search_fields = ('user__email', 'user__first_name')
    date_hierarchy = 'start_date'
    readonly_fields = ('extended_count', 'last_extended_date', 'get_privileges_display')

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'plan', 'is_active')
        }),
        ('Даты', {
            'fields': ('start_date', 'end_date')
        }),
        ('Продления', {
            'fields': ('extended_count', 'last_extended_date')
        }),
        ('Привилегии', {
            'fields': ('get_privileges_display',),
            'classes': ('wide',)
        }),
        ('Платежная информация', {
            'fields': ('yookassa_payment_id',)
        }),
    )

    def get_privileges_display(self, obj):
        """Отображает привилегии подписки"""
        privileges = obj.get_privileges()
        if not privileges:
            return "Нет привилегий"
        return "<br>".join([f"• {p.name}: {p.description}" for p in privileges])

    get_privileges_display.short_description = 'Доступные привилегии'
    get_privileges_display.allow_tags = True


@admin.register(ExtensionHistory)
class ExtensionHistoryAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'months_added', 'amount_paid', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('subscription__user__email',)
    readonly_fields = ('created_at',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'yookassa_payment_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Privilege)
class PrivilegeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'privilege_type', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    search_fields = ('name', 'code', 'description')
    list_filter = ('privilege_type', 'is_active')
    ordering = ('order', 'name')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'code')
        }),
        ('Настройки', {
            'fields': ('privilege_type', 'value', 'icon')
        }),
        ('Отображение', {
            'fields': ('is_active', 'order')
        }),
    )


class SubscriptionPlanPrivilegesInline(admin.TabularInline):
    """Инлайн для управления привилегиями прямо в форме тарифа"""
    model = SubscriptionPlan.privileges.through
    extra = 1
    verbose_name = 'Привилегия'
    verbose_name_plural = 'Привилегии тарифа'
