from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# Если модель Subscription тоже находится в другом приложении (например, 'payments'),
# замените 'subscriptions.Subscription' на соответствующее имя.
# Здесь для примера Subscription определена в текущем файле,
# но вы можете вынести её в отдельное приложение и использовать строковую ссылку.

class Subscription(models.Model):
    """Модель видов подписки (можно вынести в отдельное приложение)"""
    name = models.CharField(max_length=50, unique=True, verbose_name="Название")
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="Цена")
    duration_days = models.PositiveIntegerField(default=30, verbose_name="Длительность (дни)")
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Вид подписки"
        verbose_name_plural = "Виды подписок"


class User(AbstractUser):
    """
    Кастомная модель пользователя с полями, ссылающимися на модели из приложения 'esoteric'.
    """

    # --- Подписка (ForeignKey) ---
    # Если Subscription находится в другом приложении, используйте строку 'other_app.Subscription'
    subscription = models.ForeignKey(
        Subscription,  # или 'payments.Subscription'
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Текущая подписка",
        related_name="users"
    )

    # --- Дата и время рождения ---
    birth_date = models.DateField(null=True, blank=True, verbose_name="Дата рождения")
    birth_time = models.TimeField(null=True, blank=True, verbose_name="Время рождения")

    # --- Дата последней активности ---
    last_active = models.DateTimeField(default=timezone.now, verbose_name="Последняя активность")

    # --- Связи с моделями из другого приложения (esoteric) ---
    saved_tarot_spreads = models.ManyToManyField(
        'tarot_app.TarotCard',  # ссылка на модель в приложении esoteric
        blank=True,
        verbose_name="Сохранённые расклады Таро",
        related_name="saved_by_users"
    )

    saved_runes = models.ManyToManyField(
        'tarot_app.Rune',  # ссылка на модель в приложении esoteric
        blank=True,
        verbose_name="Сохранённые руны",
        related_name="saved_by_users"
    )

    saved_human_design = models.OneToOneField(
        'tarot_app.HumanDesign',  # ссылка на модель в приложении esoteric
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Сохранённый Human Design",
        related_name="user"
    )
    # Переопределяем groups и user_permissions с уникальными обратными именами
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="tg_bot_user_set",  # уникальное имя
        related_query_name="tg_bot_user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="tg_bot_user_set",  # уникальное имя
        related_query_name="tg_bot_user",
    )

    # --- Дополнительные полезные поля ---
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="Номер телефона")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Аватар")
    email_verified = models.BooleanField(default=False, verbose_name="Email подтверждён")
    timezone = models.CharField(max_length=50, default='UTC', verbose_name="Часовой пояс")

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
