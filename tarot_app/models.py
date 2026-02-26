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
