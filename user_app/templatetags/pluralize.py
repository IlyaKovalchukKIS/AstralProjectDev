from django import template

register = template.Library()


@register.filter
def ru_pluralize(value, variants):
    """
    Склоняет слова в зависимости от числа для русского языка.
    Использование: {{ count|ru_pluralize:"привилегия,привилегии,привилегий" }}
    """
    variants = variants.split(',')
    value = abs(int(value))

    if value % 10 == 1 and value % 100 != 11:
        return variants[0]
    elif 2 <= value % 10 <= 4 and (value % 100 < 10 or value % 100 >= 20):
        return variants[1]
    else:
        return variants[2]