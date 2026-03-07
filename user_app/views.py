import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_backends
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from .forms import EmailAuthenticationForm, MysticUserCreationForm, ProfileUpdateForm
from .models import User, SubscriptionPlan, UserSubscription, Payment
import logging

logger = logging.getLogger(__name__)


# ===== ЗАГЛУШКА ДЛЯ ЮKASSA =====
# Для тестирования без реальной оплаты
# Раскомментируйте код ниже, когда будете готовы подключить реальную ЮKassa

# import yookassa
# from yookassa import Configuration, Payment as YooKassaPayment
# Configuration.configure(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY)

class MockPayment:
    """Заглушка для тестирования платежей"""

    def __init__(self, id, confirmation_url):
        self.id = id
        self.confirmation = type('obj', (object,), {'confirmation_url': confirmation_url})
        self.status = 'pending'


def create_mock_payment(amount, description, return_url):
    """Создает заглушку платежа для тестирования"""
    payment_id = str(uuid.uuid4())
    # В тестовом режиме сразу перенаправляем на страницу успеха
    return MockPayment(payment_id, return_url)


# ===== КОНЕЦ ЗАГЛУШКИ =====


def register_view(request):
    """Регистрация пользователя"""
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = MysticUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            backend = get_backends()[0]
            user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
            login(request, user)
            messages.success(request, f'Аккаунт создан! Добро пожаловать, {user.first_name or user.email}!')
            return redirect('user_app:profile')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = MysticUserCreationForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    """Вход в систему"""
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {user.get_full_name_or_email()}!')
                next_url = request.GET.get('next', 'profile')
                return redirect(next_url)
            else:
                messages.error(request, 'Неверный email или пароль.')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = EmailAuthenticationForm()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    """Выход из системы"""
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы.')
    return redirect('home')


@login_required
def profile_view(request):
    """Личный кабинет пользователя"""
    user = request.user
    active_subscription = user.get_active_subscription()
    subscriptions_history = user.subscriptions.all().order_by('-start_date')
    subscriptions_count = subscriptions_history.count()

    context = {
        'user': user,
        'active_subscription': active_subscription,
        'subscriptions_history': subscriptions_history,
        'subscriptions_count': subscriptions_count,
    }
    return render(request, 'profile.html', context)


@login_required
def profile_update_view(request):
    """Редактирование профиля"""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('user_app:profile')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки.')
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'profile_update.html', {'form': form})


@login_required
def subscription_plans_view(request):
    """Страница выбора тарифа"""
    plans = SubscriptionPlan.objects.all().order_by('order', 'price')
    active_subscription = request.user.get_active_subscription()

    context = {
        'plans': plans,
        'active_subscription': active_subscription,
    }
    return render(request, 'subscription_plans.html', context)


@login_required
def subscription_checkout_view(request, plan_id):
    """Оформление подписки (упрощенная версия без формы)"""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)

    # Проверяем активную подписку
    if request.user.get_active_subscription():
        messages.warning(request, 'У вас уже есть активная подписка')
        return redirect('user_app:subscription_plans')

    if request.method == 'POST':
        # Создаем запись о платеже в БД
        payment = Payment.objects.create(
            user=request.user,
            plan=plan,
            amount=plan.price,
            status='pending'
        )

        try:
            # ===== ТЕСТОВЫЙ РЕЖИМ (без реальной оплаты) =====
            # В тестовом режиме сразу создаем подписку
            payment.status = 'succeeded'
            payment.save()

            # Создаем подписку
            subscription = UserSubscription.objects.create(
                user=request.user,
                plan=plan,
                start_date=timezone.now(),
                is_active=True
            )

            messages.success(request, f'Подписка "{plan.name}" успешно активирована! (ТЕСТОВЫЙ РЕЖИМ)')
            return redirect('user_app:profile')

            # ===== РЕАЛЬНЫЙ РЕЖИМ (раскомментировать для ЮKassa) =====
            # # Создаем платеж в ЮKassa 
            # idempotence_key = str(uuid.uuid4())
            # 
            # yoo_payment = YooKassaPayment.create({
            #     "amount": {
            #         "value": f"{plan.price:.2f}",
            #         "currency": "RUB"
            #     },
            #     "confirmation": {
            #         "type": "redirect",
            #         "return_url": request.build_absolute_uri(
            #             reverse('user_app:subscription_success', args=[str(payment.id)])
            #         )
            #     },
            #     "capture": True,
            #     "description": f"Подписка '{plan.name}' для {request.user.email}",
            #     "metadata": {
            #         "payment_id": str(payment.id),
            #         "user_id": request.user.id,
            #         "plan_id": plan.id
            #     }
            # }, idempotence_key)
            # 
            # # Сохраняем данные платежа от ЮKassa
            # payment.yookassa_payment_id = yoo_payment.id
            # payment.yookassa_confirmation_url = yoo_payment.confirmation.confirmation_url
            # payment.save()
            # 
            # # Перенаправляем пользователя на страницу оплаты ЮKassa
            # return redirect(yoo_payment.confirmation.confirmation_url)

        except Exception as e:
            logger.error(f"Ошибка создания платежа: {e}")
            messages.error(request, 'Ошибка при создании платежа. Пожалуйста, попробуйте позже.')
            return redirect('user_app:subscription_plans')

    # GET запрос - показываем страницу подтверждения
    return render(request, 'subscription_checkout.html', {'plan': plan})


@login_required
def subscription_success_view(request, payment_id):
    """Страница успешной оплаты"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)

    # В тестовом режиме просто показываем успех
    subscription = UserSubscription.objects.filter(
        user=request.user,
        plan=payment.plan,
        is_active=True
    ).first()

    context = {
        'payment': payment,
        'subscription': subscription,
    }
    return render(request, 'subscription_success.html', context)


@login_required
def subscription_detail_view(request, subscription_id):
    """Детали подписки"""
    subscription = get_object_or_404(UserSubscription, id=subscription_id, user=request.user)

    context = {
        'subscription': subscription,
    }
    return render(request, 'subscription_detail.html', context)


@login_required
def subscription_extend_view(request, subscription_id):
    """Продление подписки"""
    subscription = get_object_or_404(UserSubscription, id=subscription_id, user=request.user)

    if not subscription.is_active:
        messages.error(request, 'Нельзя продлить неактивную подписку')
        return redirect('user_app:profile')

    if request.method == 'POST':
        # Перенаправляем на оформление нового платежа
        return redirect('user_app:subscription_checkout', plan_id=subscription.plan.id)

    context = {
        'subscription': subscription,
    }
    return render(request, 'subscription_extend.html', context)


@login_required
def subscription_history_view(request):
    """История подписок"""
    subscriptions = request.user.subscriptions.all().order_by('-start_date')

    context = {
        'subscriptions': subscriptions,
    }
    return render(request, 'subscription_history.html', context)


# Webhook для ЮKassa (закомментирован до реального подключения)
"""
@csrf_exempt
def yookassa_webhook_view(request):
    if request.method == 'POST':
        try:
            import json
            from yookassa.domain.notification import WebhookNotificationFactory

            event_json = json.loads(request.body)
            notification = WebhookNotificationFactory().create(event_json)

            if notification.event == 'payment.succeeded':
                payment_object = notification.object
                metadata = payment_object.metadata

                if metadata and 'payment_id' in metadata:
                    try:
                        payment = Payment.objects.get(id=metadata['payment_id'])
                        payment.status = 'succeeded'
                        payment.save()
                        payment.create_subscription()
                    except Payment.DoesNotExist:
                        pass

            return HttpResponse(status=200)
        except Exception:
            return HttpResponse(status=400)

    return HttpResponse(status=405)
"""