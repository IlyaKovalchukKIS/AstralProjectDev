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

    # Расчет оставшихся дней для текущей подписки
    remaining_days = 0
    if active_subscription:
        delta = active_subscription.end_date - timezone.now()
        remaining_days = max(0, delta.days)

    context = {
        'plans': plans,
        'active_subscription': active_subscription,
        'remaining_days': remaining_days,
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
        messages.warning(request, 'У вас уже есть активная подписка. Используйте смену тарифа.')
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
                status='pending',
                payment_type='subscription',  # Явно указываем тип платежа
                metadata={  # Сохраняем plan_id в metadata
                    'plan_id': plan.id,
                    'plan_name': plan.name
                }
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
def subscription_change_view(request):
    """
    Смена тарифа с пересчетом остатка
    """
    if request.method == 'GET':
        plan_id = request.GET.get('plan_id')

        if not plan_id:
            messages.error(request, 'Не указан тариф для смены')
            return redirect('user_app:subscription_plans')

        new_plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)

        # Получаем текущую активную подписку
        current_subscription = request.user.get_active_subscription()

        if not current_subscription:
            # Если нет активной подписки, просто перенаправляем на оформление
            return redirect('user_app:subscription_checkout', plan_id=plan_id)

        if current_subscription.plan.id == new_plan.id:
            messages.info(request, 'Это ваш текущий тариф')
            return redirect('user_app:subscription_plans')

        if request.method == 'POST':
            try:
                # Расчет остаточной стоимости
                remaining_days = max(0, (current_subscription.end_date - timezone.now()).days)
                total_current_days = current_subscription.plan.duration_days
                daily_rate = current_subscription.plan.price / total_current_days
                remaining_value = round(daily_rate * remaining_days, 2)

                # Расчет к оплате
                amount_to_pay = max(0, new_plan.price - remaining_value)

                # Проверяем наличие ключей ЮKassa
                if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
                    logger.error("Ключи ЮKassa не настроены в .env файле")
                    messages.error(request, 'Платежная система временно недоступна.')
                    return redirect('user_app:subscription_plans')

                # Создаем запись о платеже в БД
                payment = Payment.objects.create(
                    user=request.user,
                    subscription=current_subscription,
                    amount=amount_to_pay,
                    status='pending',
                    payment_type='change',
                    metadata={
                        'old_plan_id': current_subscription.plan.id,
                        'new_plan_id': new_plan.id,
                        'remaining_days': remaining_days,
                        'remaining_value': str(remaining_value),
                        'original_price': str(new_plan.price)
                    }
                )

                # Формируем данные для платежа
                idempotence_key = str(uuid.uuid4())
                description = f"Смена тарифа с '{current_subscription.plan.name}' на '{new_plan.name}'"
                return_url = request.build_absolute_uri(
                    reverse('user_app:subscription_success', args=[str(payment.id)])
                )

                metadata = {
                    "payment_id": str(payment.id),
                    "user_id": str(request.user.id),
                    "old_subscription_id": str(current_subscription.id),
                    "new_plan_id": str(new_plan.id),
                    "payment_type": "change",
                    "remaining_value": str(remaining_value)
                }

                # Создаем платеж в ЮKassa
                yoo_payment = create_yookassa_payment(
                    amount=amount_to_pay,
                    description=description,
                    return_url=return_url,
                    idempotence_key=idempotence_key,
                    metadata=metadata
                )

                # Сохраняем данные платежа
                payment.yookassa_payment_id = yoo_payment['id']
                payment.save()

                logger.info(f"✅ Платеж на смену тарифа #{payment.id} создан в ЮKassa")

                # Перенаправляем на оплату
                return redirect(yoo_payment['confirmation']['confirmation_url'])

            except Exception as e:
                logger.error(f"❌ Ошибка создания платежа для смены тарифа: {e}", exc_info=True)
                messages.error(request, f'Ошибка при создании платежа: {str(e)}')
                return redirect('user_app:subscription_plans')

        # GET запрос - показываем страницу подтверждения смены тарифа
        remaining_days = max(0, (current_subscription.end_date - timezone.now()).days)
        daily_rate = current_subscription.plan.price / current_subscription.plan.duration_days
        remaining_value = round(daily_rate * remaining_days, 2)
        amount_to_pay = max(0, new_plan.price - remaining_value)

        context = {
            'current_subscription': current_subscription,
            'new_plan': new_plan,
            'remaining_days': remaining_days,
            'remaining_value': remaining_value,
            'amount_to_pay': amount_to_pay,
        }
        return render(request, 'subscription_change_confirm.html', context)


@login_required
def subscription_success_view(request, payment_id):
    """
    Страница успешной оплаты (обработка возврата из ЮKassa)
    """
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    subscription = None
    previous_plan = None
    credit_used = None
    is_plan_change = False

    try:
        # Если платеж еще в статусе pending, проверяем его статус в ЮKassa
        if payment.status == 'pending' and payment.yookassa_payment_id:
            try:
                # Получаем информацию о платеже из ЮKassa
                yoo_payment = get_yookassa_payment(payment.yookassa_payment_id)
                logger.info(f"Статус платежа из ЮKassa: {yoo_payment.get('status')}")

                # Если платеж успешен, создаем подписку
                if yoo_payment['status'] == 'succeeded':
                    metadata = yoo_payment.get('metadata', {})
                    payment_type = metadata.get('payment_type', 'subscription')

                    logger.info(f"Тип платежа: {payment_type}, метаданные: {metadata}")

                    if payment_type == 'change':
                        # Обработка смены тарифа
                        is_plan_change = True
                        old_subscription_id = metadata.get('old_subscription_id')
                        new_plan_id = metadata.get('new_plan_id')
                        remaining_value = float(metadata.get('remaining_value', 0))

                        if old_subscription_id and new_plan_id:
                            try:
                                old_subscription = UserSubscription.objects.get(
                                    id=old_subscription_id,
                                    user=request.user
                                )
                                previous_plan = old_subscription.plan
                                new_plan = SubscriptionPlan.objects.get(id=new_plan_id)
                                credit_used = remaining_value

                                # Деактивируем старую подписку
                                old_subscription.is_active = False
                                old_subscription.status = 'changed'
                                old_subscription.save()

                                # Создаем новую подписку
                                subscription = UserSubscription.objects.create(
                                    user=request.user,
                                    plan=new_plan,
                                    start_date=timezone.now(),
                                    end_date=timezone.now() + timedelta(days=new_plan.duration_days),
                                    is_active=True,
                                    status='active',
                                    yookassa_payment_id=payment.yookassa_payment_id,
                                    previous_subscription=old_subscription
                                )

                                # Обновляем платеж
                                payment.subscription = subscription
                                payment.status = 'succeeded'
                                payment.save()

                                logger.info(
                                    f"✅ Тариф изменен: #{subscription.id} для пользователя {request.user.email}")
                                messages.success(request, f'✅ Тариф успешно изменен на "{new_plan.name}"!')

                            except (UserSubscription.DoesNotExist, SubscriptionPlan.DoesNotExist) as e:
                                logger.error(f"Ошибка при смене тарифа: {e}")
                                messages.error(request, 'Ошибка при смене тарифа')

                    elif payment_type == 'extension':
                        # Обработка продления
                        subscription_id = metadata.get('subscription_id')
                        extension_option_id = metadata.get('extension_option_id')

                        if subscription_id and extension_option_id:
                            try:
                                subscription = UserSubscription.objects.get(
                                    id=subscription_id,
                                    user=request.user
                                )
                                extension_option = ExtensionOption.objects.get(id=extension_option_id)

                                # Продлеваем подписку
                                days_to_add = extension_option.days
                                old_end_date = subscription.end_date

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
                                payment.status = 'succeeded'
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

                                logger.info(f"✅ Подписка #{subscription.id} продлена")
                                messages.success(request,
                                                 f'✅ Подписка успешно продлена до {new_end_date.strftime("%d.%m.%Y")}!')

                            except (UserSubscription.DoesNotExist, ExtensionOption.DoesNotExist) as e:
                                logger.error(f"Ошибка при продлении: {e}")
                                messages.error(request, 'Ошибка при продлении подписки')

                    else:  # payment_type == 'subscription' или не указан
                        # Обычная подписка (НОВАЯ)
                        plan_id = metadata.get('plan_id')

                        # Если plan_id нет в metadata, пробуем получить из payment.metadata
                        if not plan_id and payment.metadata:
                            plan_id = payment.metadata.get('plan_id')

                        logger.info(f"Обработка новой подписки, plan_id: {plan_id}")

                        if plan_id:
                            try:
                                plan = SubscriptionPlan.objects.get(id=plan_id)

                                # Проверяем, не создана ли уже подписка для этого платежа
                                existing_subscription = UserSubscription.objects.filter(
                                    yookassa_payment_id=payment.yookassa_payment_id
                                ).first()

                                if existing_subscription:
                                    subscription = existing_subscription
                                    logger.info(f"Подписка уже существует: #{subscription.id}")
                                else:
                                    # Создаем новую подписку
                                    subscription = UserSubscription.objects.create(
                                        user=request.user,
                                        plan=plan,
                                        start_date=timezone.now(),
                                        end_date=timezone.now() + timedelta(days=plan.duration_days),
                                        is_active=True,
                                        status='active',
                                        yookassa_payment_id=payment.yookassa_payment_id
                                    )
                                    logger.info(f"✅ Создана новая подписка #{subscription.id}")

                                # Обновляем платеж
                                payment.subscription = subscription
                                payment.status = 'succeeded'
                                payment.save()

                                messages.success(request, f'✅ Подписка "{plan.name}" успешно активирована!')

                            except SubscriptionPlan.DoesNotExist:
                                logger.error(f"План подписки {plan_id} не найден")
                                messages.error(request, 'Ошибка при активации подписки')
                            except Exception as e:
                                logger.error(f"Ошибка при создании подписки: {e}")
                                messages.error(request, f'Ошибка при создании подписки: {str(e)}')
                        else:
                            logger.error(f"Не указан plan_id в метаданных. Metadata: {metadata}")
                            messages.error(request, 'Не удалось определить тариф подписки')

                elif yoo_payment['status'] == 'canceled':
                    payment.status = 'canceled'
                    payment.save()
                    messages.warning(request, 'Платеж был отменен')

            except Exception as e:
                logger.error(f"Ошибка при проверке платежа в ЮKassa: {e}", exc_info=True)
                messages.error(request, 'Произошла ошибка при проверке платежа')

        # Если платеж уже успешен, пытаемся найти подписку
        elif payment.status == 'succeeded':
            subscription = payment.subscription
            is_plan_change = payment.payment_type == 'change'
            if is_plan_change and payment.metadata:
                credit_used = payment.metadata.get('remaining_value')
                previous_plan_id = payment.metadata.get('old_plan_id')
                if previous_plan_id:
                    try:
                        previous_plan = SubscriptionPlan.objects.get(id=previous_plan_id)
                    except SubscriptionPlan.DoesNotExist:
                        pass

    except Exception as e:
        logger.error(f"Ошибка в subscription_success_view: {e}", exc_info=True)
        messages.error(request, 'Произошла ошибка при обработке платежа')

    # Если подписка не найдена, пробуем получить активную подписку пользователя
    if not subscription:
        subscription = request.user.get_active_subscription()
        logger.info(f"Активная подписка пользователя: {subscription}")

    context = {
        'payment': payment,
        'subscription': subscription,
        'previous_plan': previous_plan,
        'credit_used': credit_used,
        'is_plan_change': is_plan_change,
        'is_test_mode': settings.YOOKASSA_TEST_MODE,
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
                status='pending',
                payment_type='extension'
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

                    payment_type = metadata.get('payment_type', 'subscription')

                    # Если это смена тарифа
                    if payment_type == 'change' and not payment.subscription:
                        old_subscription_id = metadata.get('old_subscription_id')
                        new_plan_id = metadata.get('new_plan_id')
                        remaining_value = float(metadata.get('remaining_value', 0))

                        if old_subscription_id and new_plan_id:
                            try:
                                old_subscription = UserSubscription.objects.get(id=old_subscription_id)
                                new_plan = SubscriptionPlan.objects.get(id=new_plan_id)

                                # Деактивируем старую подписку
                                old_subscription.is_active = False
                                old_subscription.status = 'changed'
                                old_subscription.save()

                                # Создаем новую подписку
                                subscription = UserSubscription.objects.create(
                                    user=payment.user,
                                    plan=new_plan,
                                    start_date=timezone.now(),
                                    end_date=timezone.now() + timedelta(days=new_plan.duration_days),
                                    is_active=True,
                                    status='active',
                                    yookassa_payment_id=payment.yookassa_payment_id,
                                    previous_subscription=old_subscription
                                )

                                payment.subscription = subscription
                                payment.save()

                                logger.info(f"Webhook: тариф изменен на #{subscription.id}")

                            except (UserSubscription.DoesNotExist, SubscriptionPlan.DoesNotExist) as e:
                                logger.error(f"Webhook: ошибка при смене тарифа: {e}")

                    # Если это оплата подписки (не продление)
                    elif payment_type == 'subscription' and not payment.subscription:
                        plan_id = metadata.get('plan_id')
                        if plan_id:
                            try:
                                plan = SubscriptionPlan.objects.get(id=plan_id)

                                # Создаем подписку
                                subscription = UserSubscription.objects.create(
                                    user=payment.user,
                                    plan=plan,
                                    start_date=timezone.now(),
                                    end_date=timezone.now() + timedelta(days=plan.duration_days),
                                    is_active=True,
                                    status='active',
                                    yookassa_payment_id=payment.yookassa_payment_id
                                )

                                payment.subscription = subscription
                                payment.save()

                                logger.info(
                                    f"Webhook: подписка #{subscription.id} создана для пользователя {payment.user.id}")

                            except SubscriptionPlan.DoesNotExist:
                                logger.error(f"Webhook: план {plan_id} не найден")

                    # Если это продление подписки
                    elif payment_type == 'extension' and not payment.subscription:
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


@login_required
def subscription_change_view(request, plan_id=None):
    """
    Смена тарифа с пересчетом остатка
    Поддерживает два режима:
    - GET /subscription/change/?plan_id=XXX - страница подтверждения
    - POST /subscription/change/ - создание платежа
    - GET /subscription/change/<plan_id>/ - страница подтверждения
    """

    # Получаем текущую активную подписку
    current_subscription = request.user.get_active_subscription()

    # Если нет активной подписки, перенаправляем на оформление новой
    if not current_subscription:
        messages.info(request, 'У вас нет активной подписки. Оформите новую.')
        return redirect('user_app:subscription_plans')

    # GET запрос - показываем страницу подтверждения смены тарифа
    if request.method == 'GET':
        # Получаем ID нового тарифа из параметров URL
        if plan_id:
            target_plan_id = plan_id
        else:
            target_plan_id = request.GET.get('plan_id')

        if not target_plan_id:
            messages.error(request, 'Не указан тариф для смены')
            return redirect('user_app:subscription_plans')

        try:
            new_plan = SubscriptionPlan.objects.get(id=target_plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            messages.error(request, 'Указанный тариф не найден')
            return redirect('user_app:subscription_plans')

        # Проверяем, не пытается ли пользователь сменить на тот же тариф
        if current_subscription.plan.id == new_plan.id:
            messages.info(request, 'Это ваш текущий тариф')
            return redirect('user_app:subscription_plans')

        # Расчет остаточной стоимости текущей подписки
        now = timezone.now()

        # Если подписка еще не началась, используем дату начала
        if now < current_subscription.start_date:
            remaining_days = current_subscription.plan.duration_days
        else:
            # Рассчитываем оставшиеся дни
            delta = current_subscription.end_date - now
            remaining_days = max(0, delta.days)
            # Добавляем остаток часов как долю дня
            remaining_days += delta.seconds / 86400  # 86400 секунд в дне

        # Рассчитываем дневную ставку текущего тарифа
        total_current_days = current_subscription.plan.duration_days
        daily_rate = float(current_subscription.plan.price) / total_current_days

        # Стоимость остатка
        remaining_value = round(daily_rate * remaining_days, 2)

        # Стоимость нового тарифа
        new_plan_price = float(new_plan.price)

        # Сумма к доплате
        amount_to_pay = max(0, new_plan_price - remaining_value)

        # Применяем скидку за смену тарифа (если нужно)
        discount_amount = 0
        # Например, скидка 10% при апгрейде
        if new_plan_price > float(current_subscription.plan.price):
            discount_amount = round(amount_to_pay * 0.1, 2)
            amount_to_pay = max(0, amount_to_pay - discount_amount)

        context = {
            'current_subscription': current_subscription,
            'new_plan': new_plan,
            'remaining_days': round(remaining_days, 1),
            'remaining_value': remaining_value,
            'amount_to_pay': amount_to_pay,
            'discount_amount': discount_amount,
        }
        return render(request, 'subscription_change.html', context)

    # POST запрос - создаем платеж
    elif request.method == 'POST':
        try:
            # Получаем данные из формы
            new_plan_id = request.POST.get('new_plan_id')
            if not new_plan_id:
                messages.error(request, 'Не указан тариф для смены')
                return redirect('user_app:subscription_plans')

            new_plan = get_object_or_404(SubscriptionPlan, id=new_plan_id)

            # Повторно рассчитываем остаточную стоимость
            now = timezone.now()
            delta = current_subscription.end_date - now
            remaining_days = max(0, delta.days) + delta.seconds / 86400

            total_current_days = current_subscription.plan.duration_days
            daily_rate = float(current_subscription.plan.price) / total_current_days
            remaining_value = round(daily_rate * remaining_days, 2)

            amount_to_pay = max(0, float(new_plan.price) - remaining_value)

            # Если сумма к оплате 0 или отрицательная, активируем сразу
            if amount_to_pay <= 0:
                # Деактивируем старую подписку
                current_subscription.is_active = False
                current_subscription.status = 'changed'
                current_subscription.save()

                # Создаем новую подписку
                new_subscription = UserSubscription.objects.create(
                    user=request.user,
                    plan=new_plan,
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=new_plan.duration_days),
                    is_active=True,
                    status='active',
                    previous_subscription=current_subscription
                )

                messages.success(request, f'✅ Тариф успешно изменен на "{new_plan.name}"!')
                return redirect('user_app:subscription_detail', subscription_id=new_subscription.id)

            # Создаем платеж
            payment = Payment.objects.create(
                user=request.user,
                subscription=current_subscription,
                amount=amount_to_pay,
                status='pending',
                payment_type='change',
                metadata={
                    'old_plan_id': current_subscription.plan.id,
                    'new_plan_id': new_plan.id,
                    'old_subscription_id': current_subscription.id,
                    'remaining_days': remaining_days,
                    'remaining_value': str(remaining_value),
                    'original_price': str(new_plan.price),
                    'amount_to_pay': str(amount_to_pay)
                }
            )

            # Проверяем наличие ключей ЮKassa
            if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
                logger.error("Ключи ЮKassa не настроены в .env файле")
                messages.error(request, 'Платежная система временно недоступна.')
                return redirect('user_app:subscription_plans')

            # Формируем данные для платежа
            idempotence_key = str(uuid.uuid4())
            description = f"Смена тарифа с '{current_subscription.plan.name}' на '{new_plan.name}'"
            return_url = request.build_absolute_uri(
                reverse('user_app:subscription_success', args=[str(payment.id)])
            )

            metadata = {
                "payment_id": str(payment.id),
                "user_id": str(request.user.id),
                "old_subscription_id": str(current_subscription.id),
                "new_plan_id": str(new_plan.id),
                "payment_type": "change",
                "remaining_value": str(remaining_value)
            }

            # Создаем платеж в ЮKassa
            yoo_payment = create_yookassa_payment(
                amount=amount_to_pay,
                description=description,
                return_url=return_url,
                idempotence_key=idempotence_key,
                metadata=metadata
            )

            # Сохраняем данные платежа
            payment.yookassa_payment_id = yoo_payment['id']
            payment.save()

            logger.info(f"✅ Платеж на смену тарифа #{payment.id} создан в ЮKassa")

            # Перенаправляем на оплату
            return redirect(yoo_payment['confirmation']['confirmation_url'])

        except Exception as e:
            logger.error(f"❌ Ошибка создания платежа для смены тарифа: {e}", exc_info=True)
            messages.error(request, f'Ошибка при создании платежа: {str(e)}')
            return redirect('user_app:subscription_plans')
