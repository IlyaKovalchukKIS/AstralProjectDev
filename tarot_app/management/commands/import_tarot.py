import json
from django.core.management.base import BaseCommand
from tarot_app.models import TarotCard  # замените your_app


class Command(BaseCommand):
    help = 'Импорт карт Таро из JSON файла'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Путь к JSON файлу')

    def handle(self, *args, **options):
        file_path = options['json_file']

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                cards_data = json.load(file)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл {file_path} не найден'))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR('Ошибка в формате JSON'))
            return

        created_count = 0
        updated_count = 0

        for card_data in cards_data:
            card, created = TarotCard.objects.update_or_create(
                name=card_data['name'],
                defaults={
                    'arcana_type': card_data['arcana_type'],
                    'number': card_data['number'],
                    'description': card_data['description'],
                    'description_flip': card_data['description_flip']
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Создана: {card.name}'))
            else:
                updated_count += 1
                self.stdout.write(f'Обновлена: {card.name}')

        self.stdout.write(self.style.SUCCESS(
            f'\nГотово! Создано: {created_count}, Обновлено: {updated_count}'
        ))