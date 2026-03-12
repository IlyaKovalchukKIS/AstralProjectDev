from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid
from datetime import timedelta


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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email

    def get_full_name_or_email(self):
        """Возвращает полное имя или email, если имя не указано"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        else:
            return self.email

    def get_active_subscription(self):
        """Возвращает активную подписку пользователя"""
        now = timezone.now()
        active_sub = self.subscriptions.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).first()

        if not active_sub:
            active_sub = self.subscriptions.filter(is_active=True).first()
            if active_sub and active_sub.end_date and active_sub.end_date < now:
                active_sub.is_active = False
                active_sub.save()
                active_sub = None

        return active_sub


class Privilege(models.Model):
    """
    Модель привилегий, доступных в подписках.
    """
    PRIVILEGE_TYPES = [
        ('feature', 'Функция'),
        ('access', 'Доступ'),
        ('limit', 'Лимит'),
        ('bonus', 'Бонус'),
    ]

    name = models.CharField(
        max_length=100,
        verbose_name='Название привилегии'
    )
    description = models.TextField(
        verbose_name='Описание привилегии'
    )
    privilege_type = models.CharField(
        max_length=20,
        choices=PRIVILEGE_TYPES,
        default='feature',
        verbose_name='Тип привилегии'
    )
    icon = models.CharField(
        max_length=50,
        default='fa-solid fa-star',
        verbose_name='Иконка FontAwesome',
        help_text='Класс иконки, например: fa-solid fa-crown'
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Код привилегии',
        help_text='Уникальный код для проверки в коде, например: "tarot_reading"'
    )
    value = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Значение',
        help_text='Числовое значение (лимиты) или дополнительная информация'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активно'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок сортировки'
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
        verbose_name = 'Привилегия'
        verbose_name_plural = 'Привилегии'
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_privilege_type_display()})"


class SubscriptionPlan(models.Model):
    """
    Модель тарифного плана подписки с привилегиями.
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

    # Связь с привилегиями (многие ко многим)
    privileges = models.ManyToManyField(
        Privilege,
        blank=True,
        related_name='subscription_plans',
        verbose_name='Привилегии'
    )

    is_popular = models.BooleanField(
        default=False,
        verbose_name='Популярный тариф'
    )

    # ДОБАВЛЯЕМ ЭТО ПОЛЕ:
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок сортировки'
    )

    # Визуальные настройки
    color = models.CharField(
        max_length=20,
        default='#8b5cf6',
        verbose_name='Цвет тарифа',
        help_text='HEX код цвета, например: #8b5cf6'
    )
    icon = models.CharField(
        max_length=50,
        default='fa-solid fa-crown',
        verbose_name='Иконка тарифа'
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
        verbose_name = 'Тарифный план'
        verbose_name_plural = 'Тарифные планы'
        ordering = ['order', 'price']

    def __str__(self):
        return f"{self.name} - {self.price}₽/{self.duration_days}дн"

    def get_privileges_list(self):
        """Возвращает список привилегий для отображения"""
        return self.privileges.filter(is_active=True).order_by('order')


class ExtensionOption(models.Model):
    """
    Модель варианта продления подписки.
    Создается и редактируется через админку.
    """
    name = models.CharField(
        max_length=100,
        verbose_name='Название варианта'
    )
    months = models.PositiveIntegerField(
        verbose_name='Количество месяцев'
    )
    days = models.PositiveIntegerField(
        verbose_name='Количество дней',
        help_text='Автоматически рассчитывается на основе месяцев, но можно указать вручную'
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Скидка (%)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активно'
    )
    is_popular = models.BooleanField(
        default=False,
        verbose_name='Популярный вариант'
    )
    icon = models.CharField(
        max_length=50,
        default='fa-solid fa-moon',
        verbose_name='Иконка FontAwesome',
        help_text='Класс иконки, например: fa-solid fa-moon'
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Краткое описание'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок сортировки'
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
        verbose_name = 'Вариант продления'
        verbose_name_plural = 'Варианты продления'
        ordering = ['order', 'months']

    def __str__(self):
        discount_text = f" со скидкой {self.discount_percent}%" if self.discount_percent > 0 else ""
        return f"{self.name} ({self.months} мес{discount_text})"

    def save(self, *args, **kwargs):
        # Если дни не указаны, рассчитываем из месяцев (30 дней = 1 месяц)
        if not self.days:
            self.days = self.months * 30
        super().save(*args, **kwargs)

    def calculate_price(self, base_price):
        """
        Рассчитывает цену со скидкой на основе базовой цены тарифа
        """
        original_price = float(base_price) * self.months
        discount_multiplier = 1 - (float(self.discount_percent) / 100)
        final_price = original_price * discount_multiplier
        return {
            'original': round(original_price),
            'final': round(final_price),
            'monthly': round(float(base_price))
        }


class UserSubscription(models.Model):
    """
    Модель подписки пользователя с поддержкой продлений.
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

    # Поля для отслеживания продлений
    extended_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Количество продлений'
    )
    last_extended_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата последнего продления'
    )

    # Поле для хранения ID платежа из ЮKassa
    yookassa_payment_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='ID платежа в ЮKassa'
    )
    previous_subscription = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                              related_name='next_subscription')
    status = models.CharField(max_length=20, default='active')  # active, cancelled, changed, expired

    class Meta:
        verbose_name = 'Подписка пользователя'
        verbose_name_plural = 'Подписки пользователей'
        ordering = ['-start_date']

    def __str__(self):
        status = "Активна" if self.is_active else "Завершена"
        return f'{self.user.email} – {self.plan.name} ({status})'

    def save(self, *args, **kwargs):
        if not self.end_date and self.plan:
            self.end_date = self.start_date + timedelta(days=self.plan.duration_days)
        super().save(*args, **kwargs)

    def deactivate_if_expired(self):
        if self.end_date and self.end_date < timezone.now():
            self.is_active = False
            self.save(update_fields=['is_active'])

    def get_progress_percentage(self):
        if not self.end_date or not self.start_date:
            return 0

        now = timezone.now()
        total_seconds = (self.end_date - self.start_date).total_seconds()
        passed_seconds = (now - self.start_date).total_seconds()

        if passed_seconds <= 0:
            return 0
        if passed_seconds >= total_seconds:
            return 100

        return int((passed_seconds / total_seconds) * 100)

    def get_days_left(self):
        if not self.end_date:
            return 0
        now = timezone.now()
        if now > self.end_date:
            return 0
        delta = self.end_date - now
        return delta.days

    def get_privileges(self):
        """Возвращает все привилегии, доступные по этой подписке"""
        return self.plan.privileges.filter(is_active=True).order_by('order')

    def has_privilege(self, privilege_code):
        """Проверяет, есть ли у подписки определенная привилегия по коду"""
        return self.plan.privileges.filter(code=privilege_code, is_active=True).exists()

    def extend(self, extension_option, payment_id=None):
        """
        Продлевает подписку на основе выбранного варианта продления
        """
        days = extension_option.days

        if self.end_date > timezone.now():
            # Если подписка активна, добавляем дни к текущей дате окончания
            self.end_date = self.end_date + timedelta(days=days)
        else:
            # Если подписка истекла, начинаем с текущей даты
            self.end_date = timezone.now() + timedelta(days=days)
            self.is_active = True

        self.extended_count += 1
        self.last_extended_date = timezone.now()

        if payment_id:
            self.yookassa_payment_id = payment_id

        self.save()

        # Создаем запись в истории продлений
        ExtensionHistory.objects.create(
            subscription=self,
            extension_option=extension_option,
            old_end_date=self.end_date - timedelta(days=days),
            new_end_date=self.end_date,
            payment_id=payment_id
        )

        return self


class ExtensionHistory(models.Model):
    """
    Модель для хранения истории продлений подписок
    """
    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.CASCADE,
        related_name='extension_history',
        verbose_name='Подписка'
    )
    extension_option = models.ForeignKey(
        'ExtensionOption',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Вариант продления'
    )
    months_added = models.PositiveIntegerField(
        verbose_name='Добавлено месяцев'
    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Скидка (%)'
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Сумма оплаты'
    )
    old_end_date = models.DateTimeField(
        verbose_name='Старая дата окончания'
    )
    new_end_date = models.DateTimeField(
        verbose_name='Новая дата окончания'
    )
    payment_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='ID платежа'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата продления'
    )

    class Meta:
        verbose_name = 'История продления'
        verbose_name_plural = 'История продлений'
        ordering = ['-created_at']

    def __str__(self):
        return f'Продление #{self.id} - {self.subscription} +{self.months_added}мес'


class Payment(models.Model):
    """
    Модель для отслеживания платежей
    """
    PAYMENT_STATUS = [
        ('pending', 'Ожидает оплаты'),
        ('succeeded', 'Успешно'),
        ('canceled', 'Отменен'),
    ]
    PAYMENT_TYPES = (
        ('subscription', 'Новая подписка'),
        ('extension', 'Продление'),
        ('change', 'Смена тарифа'),
    )
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID платежа'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Пользователь'
    )
    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name='Подписка'
    )
    extension_option = models.ForeignKey(
        'ExtensionOption',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Вариант продления'
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
    yookassa_payment_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='ID платежа в ЮKassa'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, default='subscription')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']

    def __str__(self):
        return f'Платеж {self.id} - {self.amount}₽ - {self.get_status_display()}'
