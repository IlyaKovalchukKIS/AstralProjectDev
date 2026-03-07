from django.contrib import admin
from .models import (
    User, SubscriptionPlan, ExtensionOption,
    UserSubscription, ExtensionHistory, Payment
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_active', 'is_staff')
    ordering = ('-date_joined',)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'is_popular', 'order')
    list_editable = ('price', 'duration_days', 'is_popular', 'order')
    search_fields = ('name',)
    list_filter = ('is_popular',)


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
    list_filter = ('is_active', 'plan')
    search_fields = ('user__email', 'user__first_name')
    date_hierarchy = 'start_date'
    readonly_fields = ('extended_count', 'last_extended_date')


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