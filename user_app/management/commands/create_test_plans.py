from django.core.management.base import BaseCommand
from user_app.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Создает тестовые тарифные планы'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'Новолуние',
                'price': 390.00,
                'duration_days': 7,
                'description': 'Базовый доступ на неделю. Идеально для знакомства с миром магии.',
                'is_popular': False,
                'order': 1
            },
            {
                'name': 'Полнолуние',
                'price': 790.00,
                'duration_days': 30,
                'description': 'Полный доступ на месяц. Самый популярный тариф среди искателей истины.',
                'is_popular': True,
                'order': 2
            },
            {
                'name': 'Затмение',
                'price': 1990.00,
                'duration_days': 90,
                'description': 'Премиум доступ на 3 месяца. Для тех, кто готов к глубокому погружению.',
                'is_popular': False,
                'order': 3
            },
            {
                'name': 'Вечность',
                'price': 5990.00,
                'duration_days': 365,
                'description': 'Годовая подписка с максимальной выгодой. Откройте все тайны мироздания.',
                'is_popular': False,
                'order': 4
            },
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Создан тариф: {plan.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Тариф уже существует: {plan.name}'))