import json
from gigachat import GigaChat
from decouple import config

API_KEY = config("GIGACHAT_API_KEY")


def get_tarot_reading(question: str, cards: list, spread_type: str) -> str:
    """
    Получает толкование расклада Таро от GigaChat

    Args:
        question: вопрос пользователя
        cards: список карт в раскладе
        spread_type: тип расклада

    Returns:
        str: ответ нейросети с толкованием
    """
    try:
        with GigaChat(credentials=API_KEY, verify_ssl_certs=False) as giga:

            # Формируем промпт для нейросети
            prompt = create_tarot_prompt(question, cards, spread_type)

            response = giga.chat(prompt)
            return response.choices[0].message.content

    except Exception as e:
        print(f"Ошибка при обращении к GigaChat: {e}")
        return "Извините, произошла ошибка при получении ответа от нейросети. Пожалуйста, попробуйте позже."


def create_tarot_prompt(question: str, cards: list, spread_type: str) -> str:
    """
    Создает промпт для нейросети на основе вопроса и карт
    """
    # Описания типов раскладов
    spread_descriptions = {
        'one': 'Расклад на одну карту - простой ответ на вопрос',
        'three': 'Расклад на три карты (прошлое-настоящее-будущее)',
        'celtic': 'Кельтский крест - подробный расклад из 10 позиций'
    }

    # Формируем описание карт
    cards_description = []
    for i, card in enumerate(cards):
        position = ""
        if spread_type == 'celtic' and i < 10:
            positions = [
                "1. Настоящее (ситуация здесь и сейчас)",
                "2. Препятствие (что мешает)",
                "3. Прошлое (истоки ситуации)",
                "4. Будущее (ближайшее развитие)",
                "5. Сознание (что думает вопрошающий)",
                "6. Подсознание (скрытые влияния)",
                "7. Совет (как действовать)",
                "8. Окружение (влияние других людей)",
                "9. Надежды и страхи",
                "10. Итог (конечный результат)"
            ]
            position = positions[i]
        elif spread_type == 'three':
            positions = ["Прошлое", "Настоящее", "Будущее"]
            position = f"{i + 1}. {positions[i]}"
        else:
            position = f"Карта {i + 1}"

        card_status = "в перевернутом положении" if card.get('is_upside_down') else "в прямом положении"
        cards_description.append(f"{position}: {card['name']} ({card_status})")

    prompt = f"""Ты - опытный таролог с глубокими знаниями в области Таро. 
Дай подробное и вдумчивое толкование расклада на основе вопроса пользователя.

Тип расклада: {spread_descriptions.get(spread_type, spread_type)}

Вопрос пользователя: "{question}"

Карты в раскладе:
{chr(10).join(cards_description)}

Пожалуйста, дай толкование этого расклада, учитывая:
1. Связь карт с вопросом пользователя
2. Взаимодействие карт между собой (если карт несколько)
3. Значение позиций в раскладе
4. Практические советы на основе расклада

Ответ должен быть подробным, но не слишком длинным (3-5 абзацев), написан на русском языке в дружелюбном, но профессиональном тоне.
"""

    return prompt