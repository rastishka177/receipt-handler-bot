import yadisk
from receipt_handler_bot.config import YANDEX_TOKEN

y = yadisk.YaDisk(token=YANDEX_TOKEN)

def upload_file(local_path, remote_path):
    """
    Загружает файл на Яндекс.Диск
    :param local_path: локальный путь (например, ./data/cheque.jpg)
    :param remote_path: путь на Диске (например, /Проект/Администрация/cheque.jpg)
    :return: ссылка для просмотра
    """
    try:
        y.upload(local_path, remote_path, overwrite=True)
        # Делаем файл публичным и получаем ссылку
        public_link = y.publish(remote_path)
        return public_link.url
    except Exception as e:
        print(f"Ошибка при загрузке в Яндекс.Диск: {e}")
        return None
