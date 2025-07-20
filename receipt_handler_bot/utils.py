
import datetime
def generate_receipt_code(project_code, department_code, index):
    """
    Генерирует уникальный код чека.
    :param project_code: например, 'КОЛ'
    :param department_code: например, 'ПМ'
    :param index: порядковый номер, например, 1
    :return: строка, например, 'КОЛ-ПМ-01'
    """
    return f"{project_code}-{department_code}-{index:02d}"

def get_current_date():
    """
    Текущая дата в формате ДД.ММ.ГГГГ
    """
    return datetime.datetime.now().strftime("%d.%m.%Y")
