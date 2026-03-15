from django.core.management.base import BaseCommand
from user_app.models import Privilege


class Command(BaseCommand):
    help = 'Создает начальные привилегии для подписок'

    def handle(self, *args, **options):
        privileges_data = [
            {
                'name': 'Чтение Таро',
                'description': 'Доступ к онлайн-гаданию на картах Таро',
                'code': 'tarot_reading',
                'privilege_type': 'feature',
                'icon': 'fa-solid fa-crown',
                'order': 10
            },
            {
                'name': 'Руны',
                'description': 'Доступ к гаданию на Рунах',
                'code': 'runes_reading',
                'privilege_type': 'feature',
                'icon': 'fa-solid fa-wand-sparkles',
                'order': 20
            },
            {
                'name': 'Астрология',
                'description': 'Доступ к астрологическим прогнозам',
                'code': 'astrology',
                'privilege_type': 'feature',
                'icon': 'fa-solid fa-star',
                'order': 30
            },
            {
                'name': 'Human Design',
                'description': 'Доступ к расшифровке Human Design',
                'code': 'human_design',
                'privilege_type': 'feature',
                'icon': 'fa-solid fa-dragon',
                'order': 40
            },
            {
                'name': 'Маг-консультант',
                'description': 'Личный маг-консультант 24/7',
                'code': 'personal_consultant',
                'privilege_type': 'bonus',
                'icon': 'fa-solid fa-headset',
                'order': 50
            },
            {
                'name': 'Сохранение истории',
                'description': 'Сохранение истории всех гаданий',
                'code': 'history_save',
                'privilege_type': 'feature',
                'icon': 'fa-solid fa-clock-rotate-left',
                'order': 60
            },
            {
                'name': 'Без рекламы',
                'description': 'Отключение всей рекламы на сайте',
                'code': 'no_ads',
                'privilege_type': 'bonus',
                'icon': 'fa-solid fa-ban',
                'order': 70
            },
            {
                'name': 'Эксклюзивные ритуалы',
                'description': 'Доступ к закрытым ритуалам',
                'code': 'exclusive_rituals',
                'privilege_type': 'feature',
                'icon': 'fa-solid fa-mask',
                'order': 80
            },
        ]

        for priv_data in privileges_data:
            priv, created = Privilege.objects.get_or_create(
                code=priv_data['code'],
                defaults=priv_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Создана привилегия: {priv.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Привилегия уже существует: {priv.name}')
                )