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

