import logging
import os
from logging.handlers import RotatingFileHandler
import tempfile

def setup_logger():
    # Создание основного логгера
    logger = logging.getLogger('project_logger')
    logger.setLevel(logging.DEBUG)  # Уровень DEBUG позволит логировать всё

    # Создание временной директории, если её нет
    temp_dir = tempfile.gettempdir()  # Получаем путь к временной директории <button class="citation-flag" data-index="10">
    log_file_path = os.path.join(temp_dir, 'app.log')  # Путь к файлу логов

    # Обработчик для записи в файл
    file_handler = RotatingFileHandler(log_file_path, maxBytes=1024 * 1024 * 5, backupCount=3)
    file_handler.setLevel(logging.DEBUG)  # Все уровни в файл

    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Только INFO и выше в консоль

    # Форматирование логов
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Добавление обработчиков к логгеру
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"Логирование настроено. Логи будут сохраняться в {log_file_path}")  # Информационное сообщение о пути к логам

    return logger