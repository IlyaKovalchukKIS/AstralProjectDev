import random


def get_random_cards(all_cards, count):
    """
    Более компактная версия с использованием встроенных функций
    """
    if not all_cards or count <= 0:
        return []

    # Выбираем случайные карты
    selected = random.sample(all_cards, min(count, len(all_cards)))

    # Добавляем поле is_upside_down
    result = []
    for card in selected:
        if isinstance(card, dict):
            card_copy = card.copy()
            card_copy['is_upside_down'] = random.random() < 0.3
        else:
            # Для объектов можно использовать dataclasses или простые классы
            card_copy = card  # или создайте копию соответствующим образом
            card_copy.is_upside_down = random.random() < 0.3

        result.append(card_copy)

    return result