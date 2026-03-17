from django.conf import settings
from django.db import models


class TarotCard(models.Model):
    MAIOR_ARCANA = 'Ст. Аркан'
    MINOR_ARCANA = 'Мл. Аркан'

    ARCANA_CHOICES = [
        (MAIOR_ARCANA, 'Старший Аркан'),
        (MINOR_ARCANA, 'Младший Аркан'),
    ]

    name = models.CharField('Название', max_length=100)
    arcana_type = models.CharField('Тип аркана', max_length=20, choices=ARCANA_CHOICES, default=MINOR_ARCANA)
    number = models.PositiveIntegerField('Номер карты', blank=True, null=True)
    description = models.TextField('Прямое значение')
    description_flip = models.TextField('Перевёрнутое значение', blank=True)
    image = models.ImageField('Изображение', upload_to='tarot/', blank=True, null=True)

    class Meta:
        verbose_name = 'Карта Таро'
        verbose_name_plural = 'Карты Таро'
        ordering = ['number', 'name']

    def __str__(self):
        return self.name


class TarotSpread(models.Model):
    """
    Модель для сохранения раскладов Таро с привязкой к пользователю
    """
    SPREAD_TYPES = [
        ('one', 'Одна карта'),
        ('three', 'Три карты'),
        ('celtic', 'Кельтский крест'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tarot_spreads',
        verbose_name='Пользователь'
    )
    spread_type = models.CharField(
        max_length=20,
        choices=SPREAD_TYPES,
        verbose_name='Тип расклада'
    )
    question = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Вопрос'
    )
    cards_data = models.JSONField(
        verbose_name='Данные карт',
        help_text='JSON с информацией о картах в раскладе'
    )
    ai_response = models.TextField(
        blank=True,
        verbose_name='Ответ нейросети'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    is_favorite = models.BooleanField(
        default=False,
        verbose_name='Избранный'
    )
    note = models.TextField(
        blank=True,
        verbose_name='Заметка'
    )

    class Meta:
        verbose_name = 'Расклад Таро'
        verbose_name_plural = 'Расклады Таро'
        ordering = ['-created_at']

    def __str__(self):
        return f'Расклад {self.get_spread_type_display()} от {self.created_at.strftime("%d.%m.%Y %H:%M")}'

    def get_cards(self):
        """Возвращает список карт из JSON"""
        return self.cards_data.get('cards', [])

    def get_cards_count(self):
        """Возвращает количество карт в раскладе"""
        return len(self.get_cards())

    def to_dict(self):
        """Преобразует расклад в словарь для JSON ответа"""
        return {
            'id': self.id,
            'type': self.spread_type,
            'type_display': self.get_spread_type_display(),
            'question': self.question,
            'date': self.created_at.isoformat(),
            'created_at': self.created_at.isoformat(),
            'cards': self.get_cards(),
            'ai_response': self.ai_response,
            'is_favorite': self.is_favorite,
            'note': self.note
        }


class Rune(models.Model):
    """Модель руны (заглушка)"""
    name = models.CharField(max_length=50, unique=True, verbose_name="Название")
    symbol = models.CharField(max_length=10, blank=True, verbose_name="Символ")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Руна"
        verbose_name_plural = "Руны"


class HumanDesign(models.Model):
    """Модель Human Design (заглушка) — предполагается, что у пользователя может быть один профиль"""
    profile_data = models.JSONField(default=dict, verbose_name="Данные Human Design")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    def __str__(self):
        return f"HumanDesign #{self.id}"

    class Meta:
        verbose_name = "Human Design"
        verbose_name_plural = "Human Designs"
