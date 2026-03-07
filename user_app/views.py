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
from datetime import timedelta

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
        return redirect('user_app:profile')

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
        return redirect('user_app:profile')

    if request.method == 'POST':
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {user.get_full_name_or_email()}!')
                next_url = request.GET.get('next', 'user_app:profile')
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
    """
    Представление для продления подписки с выбором количества месяцев
    """
    subscription = get_object_or_404(UserSubscription, id=subscription_id, user=request.user)

    if not subscription.is_active:
        messages.error(request, 'Нельзя продлить неактивную подписку')
        return redirect('user_app:profile')

    # Словарь с количеством дней для каждого варианта
    duration_map = {
        '30': {'months': 1, 'days': 30, 'discount': 0},
        '90': {'months': 3, 'days': 90, 'discount': 5},
        '180': {'months': 6, 'days': 180, 'discount': 10},
        '365': {'months': 12, 'days': 365, 'discount': 15},
    }

    if request.method == 'POST':
        # Получаем выбранную длительность из формы
        selected_duration = request.POST.get('duration', '30')

        if selected_duration not in duration_map:
            messages.error(request, 'Выбран некорректный срок продления')
            return redirect('user_app:subscription_extend', subscription_id=subscription.id)

        duration_data = duration_map[selected_duration]
        months = duration_data['months']
        days = duration_data['days']
        discount = duration_data['discount']

        # Рассчитываем цену со скидкой
        base_price = float(subscription.plan.price)
        total_price = base_price * months * (1 - discount / 100)

        # Создаем запись о платеже
        payment = Payment.objects.create(
            user=request.user,
            plan=subscription.plan,
            amount=total_price,
            status='succeeded',  # В тестовом режиме сразу успешно
            yookassa_payment_id=f"test_payment_{uuid.uuid4()}"
        )

        # Продлеваем подписку
        old_end_date = subscription.end_date

        # Если подписка еще активна, добавляем дни к текущей дате окончания
        if subscription.end_date > timezone.now():
            new_end_date = subscription.end_date + timedelta(days=days)
        else:
            # Если подписка истекла, начинаем с текущей даты
            new_end_date = timezone.now() + timedelta(days=days)
            subscription.is_active = True

        subscription.end_date = new_end_date
        subscription.save()

        # Формируем сообщение об успехе
        discount_text = f" со скидкой {discount}%" if discount > 0 else ""
        messages.success(
            request,
            f'✅ Подписка успешно продлена на {months} {"месяц" if months == 1 else "месяца"}{discount_text}! '
            f'Новая дата окончания: {new_end_date.strftime("%d.%m.%Y")}'
        )

        return redirect('user_app:subscription_detail', subscription_id=subscription.id)

    # Для GET запроса передаем данные в шаблон
    base_price = float(subscription.plan.price)

    # Рассчитываем цены для каждого варианта
    price_options = {}
    for key, data in duration_map.items():
        months = data['months']
        discount = data['discount']
        original_price = base_price * months
        final_price = original_price * (1 - discount / 100)
        price_options[key] = {
            'months': months,
            'days': data['days'],
            'discount': discount,
            'original_price': round(original_price),
            'final_price': round(final_price),
            'monthly_price': round(base_price)
        }

    context = {
        'subscription': subscription,
        'price_options': price_options,
        'base_price': round(base_price),
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