import uuid
import logging
import json
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_backends
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .forms import EmailAuthenticationForm, MysticUserCreationForm, ProfileUpdateForm
from .models import SubscriptionPlan, UserSubscription, Payment, ExtensionOption, ExtensionHistory

# Импортируем requests для прямых запросов к API ЮKassa
import requests

logger = logging.getLogger(__name__)


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ЮKASSA =====

def create_yookassa_payment(amount, description, return_url, idempotence_key, metadata=None):
    """
    Создание платежа через прямой HTTP запрос к API ЮKassa
    """
    shop_id = settings.YOOKASSA_SHOP_ID
    secret_key = settings.YOOKASSA_SECRET_KEY

    if not shop_id or not secret_key:
        raise Exception("Не настроены ключи ЮKassa в .env файле")

    # Формируем данные для платежа
    payment_data = {
        "amount": {
            "value": f"{float(amount):.2f}",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": return_url
        },
        "capture": True,
        "description": description,
        "test": settings.YOOKASSA_TEST_MODE
    }

    # Добавляем метаданные если есть
    if metadata:
        payment_data["metadata"] = metadata

    # Логируем запрос (без секретных данных)
    logger.info(f"Отправка запроса к ЮKassa: создание платежа на сумму {amount} RUB")

    try:
        # Отправляем запрос с базовой аутентификацией
        response = requests.post(
            'https://api.yookassa.ru/v3/payments',
            auth=(shop_id, secret_key),  # Важно: именно так, через кортеж
            headers={
                'Content-Type': 'application/json',
                'Idempotence-Key': idempotence_key
            },
            json=payment_data,
            timeout=30
        )

        # Логируем статус ответа
        logger.info(f"Статус ответа от ЮKassa: {response.status_code}")

        # Проверяем ответ
        if response.status_code in (200, 201):
            result = response.json()
            logger.info(f"✅ Платеж создан успешно. ID: {result.get('id')}")
            return result
        else:
            # Пытаемся получить описание ошибки
            try:
                error_data = response.json()
                error_msg = error_data.get('description', 'Неизвестная ошибка')
                error_code = error_data.get('code', '')
                error_param = error_data.get('parameter', '')

                logger.error(f"❌ Ошибка ЮKassa: {error_msg} (код: {error_code}, параметр: {error_param})")

                # Формируем понятное сообщение об ошибке
                if error_code == 'invalid_credentials':
                    raise Exception("Ошибка аутентификации в платежной системе. Проверьте ключи API.")
                elif error_code == 'bad_request':
                    raise Exception(f"Неверный запрос к платежной системе: {error_msg}")
                else:
                    raise Exception(f"Ошибка платежной системы: {error_msg}")

            except ValueError:
                # Если не удалось распарсить JSON
                response.raise_for_status()

    except requests.exceptions.Timeout:
        logger.error("❌ Таймаут при запросе к ЮKassa")
        raise Exception("Превышено время ожидания ответа от платежной системы")

    except requests.exceptions.ConnectionError:
        logger.error("❌ Ошибка подключения к ЮKassa")
        raise Exception("Не удалось подключиться к платежной системе")

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Ошибка запроса к ЮKassa: {e}")
        raise Exception(f"Ошибка при обращении к платежной системе: {str(e)}")


def get_yookassa_payment(payment_id):
    """
    Получение информации о платеже из ЮKassa
    """
    shop_id = settings.YOOKASSA_SHOP_ID
    secret_key = settings.YOOKASSA_SECRET_KEY

    if not shop_id or not secret_key:
        raise Exception("Не настроены ключи ЮKassa")

    try:
        response = requests.get(
            f'https://api.yookassa.ru/v3/payments/{payment_id}',
            auth=(shop_id, secret_key),
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        if response.status_code == 200:
            return response.json()
        else:
            try:
                error_data = response.json()
                raise Exception(error_data.get('description', 'Неизвестная ошибка'))
            except:
                response.raise_for_status()

    except Exception as e:
        logger.error(f"❌ Ошибка получения платежа из ЮKassa: {e}")
        raise


# ===== АУТЕНТИФИКАЦИЯ =====

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


# ===== ПРОФИЛЬ =====

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


# ===== ПОДПИСКИ И ПЛАТЕЖИ =====

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
    """
    Оформление подписки с оплатой через ЮKassa
    """
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)

    # Проверяем активную подписку
    if request.user.get_active_subscription():
        messages.warning(request, 'У вас уже есть активная подписка')
        return redirect('user_app:subscription_plans')

    if request.method == 'POST':
        try:
            # Проверяем наличие ключей ЮKassa
            if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
                logger.error("Ключи ЮKassa не настроены в .env файле")
                messages.error(request, 'Платежная система временно недоступна. Пожалуйста, попробуйте позже.')
                return redirect('user_app:subscription_plans')

            # Создаем запись о платеже в БД
            payment = Payment.objects.create(
                user=request.user,
                amount=plan.price,
                status='pending'
            )

            logger.info(f"Создана запись платежа #{payment.id} для пользователя {request.user.email}")

            # Формируем данные для платежа
            idempotence_key = str(uuid.uuid4())
            description = f"Подписка '{plan.name}' для {request.user.email}"
            return_url = request.build_absolute_uri(
                reverse('user_app:subscription_success', args=[str(payment.id)])
            )

            metadata = {
                "payment_id": str(payment.id),
                "user_id": str(request.user.id),
                "plan_id": str(plan.id),
                "payment_type": "subscription"
            }

            # Создаем платеж через ЮKassa
            yoo_payment = create_yookassa_payment(
                amount=float(plan.price),
                description=description,
                return_url=return_url,
                idempotence_key=idempotence_key,
                metadata=metadata
            )

            # Сохраняем данные платежа от ЮKassa
            payment.yookassa_payment_id = yoo_payment['id']
            payment.save()

            logger.info(f"✅ Платеж #{payment.id} создан в ЮKassa. ID: {yoo_payment['id']}")

            # Перенаправляем пользователя на страницу оплаты ЮKassa
            confirmation_url = yoo_payment['confirmation']['confirmation_url']
            return redirect(confirmation_url)

        except Exception as e:
            logger.error(f"❌ Ошибка создания платежа: {str(e)}", exc_info=True)
            messages.error(request, f'Ошибка при создании платежа: {str(e)}')
            return redirect('user_app:subscription_plans')

    # GET запрос - показываем страницу подтверждения
    return render(request, 'subscription_checkout.html', {'plan': plan})


@login_required
def subscription_success_view(request, payment_id):
    """
    Страница успешной оплаты (обработка возврата из ЮKassa)
    """
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    subscription = None

    try:
        # Если платеж еще в статусе pending, проверяем его статус в ЮKassa
        if payment.status == 'pending' and payment.yookassa_payment_id:
            try:
                # Получаем информацию о платеже из ЮKassa
                yoo_payment = get_yookassa_payment(payment.yookassa_payment_id)

                # Если платеж успешен, создаем подписку
                if yoo_payment['status'] == 'succeeded':
                    # Получаем plan_id из metadata
                    metadata = yoo_payment.get('metadata', {})
                    plan_id = metadata.get('plan_id')

                    if plan_id:
                        try:
                            plan = SubscriptionPlan.objects.get(id=plan_id)

                            # Создаем подписку
                            subscription = UserSubscription.objects.create(
                                user=request.user,
                                plan=plan,
                                start_date=timezone.now(),
                                is_active=True,
                                yookassa_payment_id=payment.yookassa_payment_id
                            )

                            # Обновляем платеж
                            payment.subscription = subscription
                            payment.status = 'succeeded'
                            payment.save()

                            logger.info(f"✅ Подписка #{subscription.id} создана для пользователя {request.user.email}")
                            messages.success(request, f'✅ Подписка "{plan.name}" успешно активирована!')

                        except SubscriptionPlan.DoesNotExist:
                            logger.error(f"План подписки {plan_id} не найден")
                            messages.error(request, 'Ошибка при активации подписки')

                elif yoo_payment['status'] == 'canceled':
                    payment.status = 'canceled'
                    payment.save()
                    messages.warning(request, 'Платеж был отменен')

            except Exception as e:
                logger.error(f"Ошибка при проверке платежа в ЮKassa: {e}")

        # Если платеж уже успешен, пытаемся найти подписку
        elif payment.status == 'succeeded':
            subscription = payment.subscription

    except Exception as e:
        logger.error(f"Ошибка в subscription_success_view: {e}", exc_info=True)
        messages.error(request, 'Произошла ошибка при обработке платежа')

    # Если подписка не найдена, пробуем получить активную подписку пользователя
    if not subscription:
        subscription = request.user.get_active_subscription()

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
    Продление подписки с оплатой через ЮKassa
    """
    subscription = get_object_or_404(UserSubscription, id=subscription_id, user=request.user)

    if not subscription.is_active:
        messages.error(request, 'Нельзя продлить неактивную подписку')
        return redirect('user_app:profile')

    # Получаем все активные варианты продления из БД
    extension_options = ExtensionOption.objects.filter(is_active=True).order_by('order', 'months')

    if not extension_options.exists():
        messages.warning(request, 'Варианты продления временно недоступны')
        return redirect('user_app:subscription_detail', subscription_id=subscription.id)

    # Рассчитываем цены для каждого варианта
    price_data = {}
    base_price = float(subscription.plan.price)

    for option in extension_options:
        price_data[option.id] = option.calculate_price(base_price)

    if request.method == 'POST':
        # Получаем выбранный вариант продления
        option_id = request.POST.get('extension_option')

        if not option_id:
            messages.error(request, 'Пожалуйста, выберите вариант продления')
            return redirect('user_app:subscription_extend', subscription_id=subscription.id)

        try:
            selected_option = ExtensionOption.objects.get(id=option_id, is_active=True)
        except ExtensionOption.DoesNotExist:
            messages.error(request, 'Выбран некорректный вариант продления')
            return redirect('user_app:subscription_extend', subscription_id=subscription.id)

        # Рассчитываем цену со скидкой
        price_info = selected_option.calculate_price(base_price)

        try:
            # Проверяем наличие ключей ЮKassa
            if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
                logger.error("Ключи ЮKassa не настроены в .env файле")
                messages.error(request, 'Платежная система временно недоступна.')
                return redirect('user_app:subscription_extend', subscription_id=subscription.id)

            # Создаем запись о платеже в БД
            payment = Payment.objects.create(
                user=request.user,
                subscription=subscription,
                extension_option=selected_option,
                amount=price_info['final'],
                status='pending'
            )

            # Формируем данные для платежа
            idempotence_key = str(uuid.uuid4())
            description = f"Продление подписки '{subscription.plan.name}' на {selected_option.months} мес."
            return_url = request.build_absolute_uri(
                reverse('user_app:subscription_success', args=[str(payment.id)])
            )

            metadata = {
                "payment_id": str(payment.id),
                "user_id": str(request.user.id),
                "subscription_id": str(subscription.id),
                "extension_option_id": str(selected_option.id),
                "payment_type": "extension"
            }

            # Создаем платеж в ЮKassa
            yoo_payment = create_yookassa_payment(
                amount=price_info['final'],
                description=description,
                return_url=return_url,
                idempotence_key=idempotence_key,
                metadata=metadata
            )

            # Сохраняем данные платежа
            payment.yookassa_payment_id = yoo_payment['id']
            payment.save()

            logger.info(f"✅ Платеж на продление #{payment.id} создан в ЮKassa")

            # Перенаправляем на оплату
            return redirect(yoo_payment['confirmation']['confirmation_url'])

        except Exception as e:
            logger.error(f"❌ Ошибка создания платежа для продления: {e}", exc_info=True)
            messages.error(request, f'Ошибка при создании платежа: {str(e)}')
            return redirect('user_app:subscription_extend', subscription_id=subscription.id)

    context = {
        'subscription': subscription,
        'extension_options': extension_options,
        'price_data': price_data,
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


# ===== WEBHOOK ДЛЯ ЮKASSA =====

@csrf_exempt
def yookassa_webhook_view(request):
    """
    Webhook для получения уведомлений от ЮKassa о статусе платежей
    URL: /user/webhook/yookassa/
    """
    if request.method == 'POST':
        try:
            # Получаем данные из запроса
            event_json = json.loads(request.body)

            logger.info(f"Получен webhook от ЮKassa: {event_json.get('event')}")

            # Обрабатываем разные типы событий
            event = event_json.get('event')
            payment_object = event_json.get('object', {})

            # Получаем метаданные платежа
            metadata = payment_object.get('metadata', {})
            payment_id = metadata.get('payment_id')

            if not payment_id:
                logger.warning("Webhook: не найден payment_id в метаданных")
                return HttpResponse(status=200)

            try:
                # Находим наш платеж в БД
                payment = Payment.objects.get(id=payment_id)

                # Обрабатываем событие
                if event == 'payment.succeeded':
                    # Платеж успешен
                    logger.info(f"Webhook: платеж {payment_id} успешен")

                    payment.status = 'succeeded'
                    payment.save()

                    # Если это оплата подписки (не продление)
                    if metadata.get('payment_type') == 'subscription' and not payment.subscription:
                        plan_id = metadata.get('plan_id')
                        if plan_id:
                            try:
                                plan = SubscriptionPlan.objects.get(id=plan_id)

                                # Создаем подписку
                                subscription = UserSubscription.objects.create(
                                    user=payment.user,
                                    plan=plan,
                                    start_date=timezone.now(),
                                    is_active=True,
                                    yookassa_payment_id=payment.yookassa_payment_id
                                )

                                payment.subscription = subscription
                                payment.save()

                                logger.info(
                                    f"Webhook: подписка #{subscription.id} создана для пользователя {payment.user.id}")

                            except SubscriptionPlan.DoesNotExist:
                                logger.error(f"Webhook: план {plan_id} не найден")

                    # Если это продление подписки
                    elif metadata.get('payment_type') == 'extension' and not payment.subscription:
                        subscription_id = metadata.get('subscription_id')
                        extension_option_id = metadata.get('extension_option_id')

                        if subscription_id and extension_option_id:
                            try:
                                subscription = UserSubscription.objects.get(
                                    id=subscription_id,
                                    user=payment.user
                                )
                                extension_option = ExtensionOption.objects.get(
                                    id=extension_option_id
                                )

                                # Продлеваем подписку
                                old_end_date = subscription.end_date
                                days_to_add = extension_option.days

                                if subscription.end_date and subscription.end_date > timezone.now():
                                    new_end_date = subscription.end_date + timedelta(days=days_to_add)
                                else:
                                    new_end_date = timezone.now() + timedelta(days=days_to_add)
                                    subscription.is_active = True

                                subscription.end_date = new_end_date
                                subscription.extended_count += 1
                                subscription.last_extended_date = timezone.now()
                                subscription.save()

                                # Обновляем платеж
                                payment.subscription = subscription
                                payment.extension_option = extension_option
                                payment.save()

                                # Создаем запись в истории
                                ExtensionHistory.objects.create(
                                    subscription=subscription,
                                    extension_option=extension_option,
                                    months_added=extension_option.months,
                                    discount_percent=extension_option.discount_percent,
                                    amount_paid=payment.amount,
                                    old_end_date=old_end_date,
                                    new_end_date=new_end_date,
                                    payment_id=payment.yookassa_payment_id
                                )

                                logger.info(f"Webhook: подписка #{subscription.id} продлена")

                            except (UserSubscription.DoesNotExist, ExtensionOption.DoesNotExist) as e:
                                logger.error(f"Webhook: ошибка при продлении: {e}")

                elif event == 'payment.canceled':
                    # Платеж отменен
                    logger.info(f"Webhook: платеж {payment_id} отменен")
                    payment.status = 'canceled'
                    payment.save()

                elif event == 'refund.succeeded':
                    # Возврат средств
                    logger.info(f"Webhook: возврат средств по платежу {payment_id}")

            except Payment.DoesNotExist:
                logger.error(f"Webhook: платеж {payment_id} не найден в БД")

            return HttpResponse(status=200)

        except json.JSONDecodeError:
            logger.error("Webhook: ошибка парсинга JSON")
            return HttpResponse(status=400)

        except Exception as e:
            logger.error(f"Webhook: неожиданная ошибка: {e}", exc_info=True)
            return HttpResponse(status=500)

    return HttpResponse(status=405)
