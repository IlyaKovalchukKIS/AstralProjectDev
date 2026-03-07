from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid


class UserManager(BaseUserManager):
    """
    Кастомный менеджер для модели User с аутентификацией по email.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Создает и возвращает пользователя с email и паролем.
        """
        if not email:
            raise ValueError('Email обязателен для создания пользователя')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Создает и возвращает суперпользователя с email и паролем.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Кастомная модель пользователя.
    Аутентификация по email вместо username.
    """
    username = models.CharField(
        max_length=150,
        unique=False,
        blank=True,
        null=True,
        verbose_name='Имя пользователя (необязательно)'
    )
    email = models.EmailField(
        unique=True,
        verbose_name='Email'
    )
    phone = models.CharField(
        max_length=15,
        blank=True,
        verbose_name='Телефон'
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата рождения'
    )
    birth_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Время рождения'
    )

    # Указываем поле для аутентификации как email
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # username больше не требуется

    # Используем кастомный менеджер
    objects = UserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email

    def get_full_name_or_email(self):
        """Возвращает полное имя или email, если имя не указано"""
        full_name = self.get_full_name()
        return full_name if full_name else self.email

    def get_active_subscription(self):
        """
        Возвращает активную подписку пользователя
        """
        try:
            # Получаем текущее время
            now = timezone.now()

            # Ищем активную подписку
            active_sub = self.subscriptions.filter(
                is_active=True,
                start_date__lte=now,
                end_date__gte=now
            ).first()

            # Если не нашли по датам, пробуем просто активную
            if not active_sub:
                active_sub = self.subscriptions.filter(is_active=True).first()

                # Проверяем, не истекла ли она
                if active_sub and active_sub.end_date and active_sub.end_date < now:
                    active_sub.is_active = False
                    active_sub.save()
                    active_sub = None

            return active_sub
        except Exception as e:
            print(f"Error getting active subscription: {e}")
            return None


class SubscriptionPlan(models.Model):
    """
    Модель тарифного плана подписки.
    """
    name = models.CharField(
        max_length=100,
        verbose_name='Название тарифа'
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='Цена'
    )
    duration_days = models.PositiveIntegerField(
        default=30,
        verbose_name='Срок действия (дней)'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )

    class Meta:
        verbose_name = 'Тарифный план'
        verbose_name_plural = 'Тарифные планы'

    def __str__(self):
        return self.name


class UserSubscription(models.Model):
    """
    Модель подписки пользователя.
    Связывает пользователя с тарифным планом на определённый период.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Пользователь'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        verbose_name='Тарифный план'
    )
    start_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата начала'
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата окончания'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )

    class Meta:
        verbose_name = 'Подписка пользователя'
        verbose_name_plural = 'Подписки пользователей'
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.user.email} – {self.plan.name}'

    def deactivate_if_expired(self):
        """
        Деактивирует подписку, если её срок истёк.
        """
        if self.end_date and self.end_date < timezone.now():
            self.is_active = False
            self.save(update_fields=['is_active'])

    def save(self, *args, **kwargs):
        """
        Автоматически устанавливает дату окончания, если она не указана,
        исходя из длительности тарифа.
        """
        if not self.end_date and self.plan:
            self.end_date = self.start_date + timezone.timedelta(days=self.plan.duration_days)
        super().save(*args, **kwargs)


class Payment(models.Model):
    """
    Модель для отслеживания платежей
    """
    PAYMENT_STATUS = [
        ('pending', 'Ожидает оплаты'),
        ('processing', 'В обработке'),
        ('completed', 'Оплачен'),
        ('failed', 'Ошибка'),
        ('refunded', 'Возврат'),
    ]

    PAYMENT_METHOD = [
        ('card', 'Банковская карта'),
        ('yookassa', 'ЮKassa'),
        ('tinkoff', 'Тинькофф'),
        ('sbp', 'СБП'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Пользователь'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        verbose_name='Тарифный план'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Сумма'
    )
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default='pending',
        verbose_name='Статус'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD,
        default='card',
        verbose_name='Способ оплаты'
    )
    payment_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='ID платежа в платежной системе'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']

    def __str__(self):
        return f'Платеж {self.id} - {self.user.email} - {self.amount}₽'

    def complete_payment(self):
        """
        Завершает платеж и создает подписку
        """
        self.status = 'completed'
        self.save()

        # Создаем подписку
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            start_date=timezone.now(),
            is_active=True
        )
        return subscription
