from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, get_backends
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import EmailAuthenticationForm, MysticUserCreationForm, ProfileUpdateForm
from .models import UserSubscription, SubscriptionPlan


def login_view(request):
    """
    Представление для входа в систему.
    """
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
                messages.success(request, f'Добро пожаловать в мир мистики, {user.get_full_name_or_email()}!')
                next_url = request.GET.get('next', 'user_app:profile')
                return redirect(next_url)
            else:
                messages.error(request, 'Неверный email или пароль.')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = EmailAuthenticationForm()

    return render(request, 'login.html', {'form': form})


def register_view(request):
    """
    Представление для регистрации нового пользователя.
    """
    if request.user.is_authenticated:
        return redirect('user_app:profile')

    if request.method == 'POST':
        form = MysticUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Получаем первый доступный бэкенд аутентификации
            backend = get_backends()[0]
            user.backend = f"{backend.__module__}.{backend.__class__.__name__}"

            # Вход пользователя после регистрации
            login(request, user)

            messages.success(request,
                             f'Аккаунт создан! Добро пожаловать в мистическое сообщество, {user.first_name or user.email}!')
            return redirect('user_app:profile')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = MysticUserCreationForm()

    return render(request, 'register.html', {'form': form})


@login_required
def profile_view(request):
    """
    Представление личного кабинета пользователя.
    """
    user = request.user
    active_subscription = user.get_active_subscription()

    # Получаем все подписки пользователя для истории
    subscriptions_history = user.subscriptions.all().order_by('-start_date')
    subscriptions_count = subscriptions_history.count()

    context = {
        'user': user,
        'active_subscription': active_subscription if active_subscription else None,
        'subscriptions_history': subscriptions_history,
        'subscriptions_count': subscriptions_count,
    }
    return render(request, 'profile.html', context)


@login_required
def profile_update_view(request):
    """
    Представление для редактирования профиля.
    """
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


def logout_view(request):
    """
    Представление для выхода из системы.
    """
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы.')
    return redirect('home')


@login_required
def subscription_history_view(request):
    """
    Представление для просмотра истории всех подписок.
    """
    subscriptions = request.user.subscriptions.all().order_by('-start_date')
    return render(request, 'user_app/subscription_history.html', {
        'subscriptions': subscriptions
    })


@login_required
def subscription_detail_view(request, subscription_id):
    """
    Представление для просмотра деталей конкретной подписки.
    """
    subscription = get_object_or_404(UserSubscription, id=subscription_id, user=request.user)
    return render(request, 'user_app/subscription_detail.html', {
        'subscription': subscription
    })


@login_required
def subscription_extend_view(request, subscription_id):
    """
    Представление для продления подписки.
    """
    subscription = get_object_or_404(UserSubscription, id=subscription_id, user=request.user, is_active=True)

    if request.method == 'POST':
        # Логика продления подписки
        messages.success(request, f'Подписка "{subscription.plan.name}" успешно продлена!')
        return redirect('user_app:profile')

    return render(request, 'user_app/subscription_extend.html', {
        'subscription': subscription
    })


@login_required
def subscription_plans_view(request):
    """
    Представление для просмотра доступных тарифных планов.
    """
    plans = SubscriptionPlan.objects.all()
    return render(request, 'user_app/subscription_plans.html', {
        'plans': plans
    })


@login_required
def subscription_history_view(request):
    """
    Представление для просмотра истории всех подписок.
    """
    subscriptions = request.user.subscriptions.all().order_by('-start_date')
    return render(request, 'user_app/subscription_history.html', {
        'subscriptions': subscriptions
    })


@login_required
def subscription_detail_view(request, subscription_id):
    """
    Представление для просмотра деталей конкретной подписки.
    """
    subscription = get_object_or_404(UserSubscription, id=subscription_id, user=request.user)
    return render(request, 'user_app/subscription_detail.html', {
        'subscription': subscription
    })


@login_required
def subscription_extend_view(request, subscription_id):
    """
    Представление для продления подписки.
    """
    subscription = get_object_or_404(UserSubscription, id=subscription_id, user=request.user, is_active=True)

    if request.method == 'POST':
        # Логика продления подписки
        messages.success(request, f'Подписка "{subscription.plan.name}" успешно продлена!')
        return redirect('user_app:profile')

    return render(request, 'user_app/subscription_extend.html', {
        'subscription': subscription
    })


@login_required
def subscription_plans_view(request):
    """
    Представление для просмотра доступных тарифных планов.
    """
    plans = SubscriptionPlan.objects.all()
    return render(request, 'user_app/subscription_plans.html', {
        'plans': plans
    })
