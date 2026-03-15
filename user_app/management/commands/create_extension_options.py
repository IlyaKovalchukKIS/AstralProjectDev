from django.core.management.base import BaseCommand
from user_app.models import ExtensionOption


class Command(BaseCommand):
    help = 'Создает начальные варианты продления подписок'

    def handle(self, *args, **options):
        options_data = [
            {
                'name': '1 месяц',
                'months': 1,
                'days': 30,
                'discount_percent': 0,
                'is_popular': False,
                'icon': 'fa-solid fa-moon',
                'description': 'Продление на 1 месяц без скидки',
                'order': 1
            },
            {
                'name': '3 месяца',
                'months': 3,
                'days': 90,
                'discount_percent': 5,
                'is_popular': True,
                'icon': 'fa-solid fa-crown',
                'description': 'Продление на 3 месяца со скидкой 5%',
                'order': 2
            },
            {
                'name': '6 месяцев',
                'months': 6,
                'days': 180,
                'discount_percent': 10,
                'is_popular': False,
                'icon': 'fa-solid fa-infinity',
                'description': 'Продление на 6 месяцев со скидкой 10%',
                'order': 3
            },
            {
                'name': '12 месяцев',
                'months': 12,
                'days': 365,
                'discount_percent': 15,
                'is_popular': False,
                'icon': 'fa-solid fa-star',
                'description': 'Продление на 12 месяцев со скидкой 15%',
                'order': 4
            },
        ]

        for opt_data in options_data:
            option, created = ExtensionOption.objects.get_or_create(
                name=opt_data['name'],
                defaults=opt_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Создан вариант продления: {option.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Вариант продления уже существует: {option.name}')
                )