from django.urls import path
from . import views

app_name = 'user_app'

urlpatterns = [
    # Аутентификация
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Профиль
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update_view, name='profile_update'),

    # Подписки и оплата
    path('subscription/plans/', views.subscription_plans_view, name='subscription_plans'),
    path('subscription/checkout/<int:plan_id>/', views.subscription_checkout_view, name='subscription_checkout'),

    # ВАЖНО: Добавляем URL для смены тарифа
    path('subscription/change/', views.subscription_change_view, name='subscription_change'),
    path('subscription/change/<int:plan_id>/', views.subscription_change_view, name='subscription_change_with_plan'),

    path('subscription/success/<uuid:payment_id>/', views.subscription_success_view, name='subscription_success'),
    path('subscription/<int:subscription_id>/', views.subscription_detail_view, name='subscription_detail'),
    path('subscription/<int:subscription_id>/extend/', views.subscription_extend_view, name='subscription_extend'),
    path('subscription/history/', views.subscription_history_view, name='subscription_history'),

    # Webhook для ЮKassa
    path('webhook/yookassa/', views.yookassa_webhook_view, name='yookassa_webhook'),
]