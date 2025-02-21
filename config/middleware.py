import logging
from datetime import datetime
from pyrogram import Client

logger = logging.getLogger('project_logger')


class AntiSpamMiddleware:
    def __init__(self, app: Client):
        self.app = app
        self.user_requests = {}  # Словарь для отслеживания запросов пользователей

    async def check_spam(self, user_id: int) -> bool:
        """
        Проверяет, является ли запрос спамом.

        Args:
            user_id (int): ID пользователя.

        Returns:
            bool: True, если это спам, иначе False.
        """
        current_time = datetime.now()

        if user_id in self.user_requests:
            request_times = self.user_requests[user_id]

            # Удаляем старые записи (старше 30 секунд)
            while request_times and (current_time - request_times[0]).total_seconds() > 30:
                request_times.pop(0)

            # Если количество запросов превышает 5 за последние 30 секунд
            if len(request_times) >= 5:
                return True

            # Добавляем текущий запрос
            request_times.append(current_time)
        else:
            # Инициализируем список запросов для нового пользователя
            self.user_requests[user_id] = [current_time]

        return False

    async def process_event(self, event):
        """
        Обрабатывает событие и проверяет на наличие спама.

        Args:
            event: Объект события (сообщение или callback).
        """
        try:
            user_id = event.from_user.id if hasattr(event, 'from_user') and event.from_user else None
            if not user_id:
                return  # Пропускаем события без пользователя

            # Проверяем на спам
            if await self.check_spam(user_id):
                chat_id = event.chat.id if hasattr(event, 'chat') else event.message.chat.id
                await self.app.send_message(
                    chat_id=chat_id,
                    text="Слишком много запросов! Пожалуйста, подождите 30 секунд."
                )
                return

            # Логируем активность пользователя
            from config import log_user_activity
            log_user_activity(user_id)
        except Exception as e:
            logger.error(f"Ошибка в процессе проверки спама: {e}")


# Регистрация middleware
def register_middleware(app: Client):
    """
    Регистрирует middleware для приложения.

    Args:
        app (Client): Экземпляр Pyrogram клиента.
    """
    anti_spam_middleware = AntiSpamMiddleware(app)

    @app.on_message()
    async def on_message(message):
        await anti_spam_middleware.process_event(message)
        # Передаем управление следующим обработчикам
        app.dispatcher.trigger_handlers(message)

    @app.on_callback_query()
    async def on_callback_query(callback_query):
        await anti_spam_middleware.process_event(callback_query)
        # Передаем управление следующим обработчикам
        app.dispatcher.trigger_handlers(callback_query)