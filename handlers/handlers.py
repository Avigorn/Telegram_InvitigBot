from datetime import datetime, timedelta

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

from handlers.BaseHandler import BaseHandler
from pyrogram import Client, filters

from config import save_chat, update_chat_data, add_user
from config.config import add_message, get_users_in_chat
from logger import setup_logger

logger = setup_logger()


class StartHandler(BaseHandler):
    def __init__(self, app: Client):
        super().__init__(app)
        self.register_handlers()

    def register_handlers(self):
        @self.app.on_message(filters.command("start"))
        async def cmd_start(message):
            await message.reply_text(
                "Приветствую тебя, Шарьинец! Прочитайте описание или воспользуйтесь кнопкой Помощь:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Помощь", callback_data="help")],
                    [InlineKeyboardButton("Приглашение", callback_data="invite")],
                    [InlineKeyboardButton("Мероприятие", callback_data="event")]
                ])
            )

class HelpButton(BaseHandler):
    def __init__(self, app: Client):
        super().__init__(app)
        self.register_handlers()

    def register_handlers(self):
        @self.app.on_callback_query(filters.regex("help"))
        async def handle_help(callback_query):
            await callback_query.message.reply_text(
                "Список моих возможностей:\n"
                "• Приглашение - получить пригласительную ссылку\n"
                "• Мероприятие - отметить всех и указать причину\n"
                "• Сообщение 'Я уехал' - временно покинуть группу"
            )
            await callback_query.answer()

class InviteButton(BaseHandler):
    def __init__(self, app: Client, inviting_chat_id, invited_chat_id):
        super().__init__(app)
        self.inviting_chat_id = inviting_chat_id
        self.invited_chat_id = invited_chat_id
        self.register_handlers()

    def register_handlers(self):
        @self.app.on_callback_query(filters.regex("invite"))
        async def handle_invite(client, callback_query):
            user_id = callback_query.from_user.id

            try:
                # Проверяем права бота в чате
                bot_member = await client.get_chat_member(self.inviting_chat_id, "me")
                if bot_member.status not in ["administrator", "creator"]:
                    await client.send_message(user_id, "Бот не имеет прав для создания пригласительной ссылки.")
                    return

                chat_member = await client.get_chat_member(self.inviting_chat_id, user_id)
                if chat_member.status not in ["member", "administrator", "creator"]:
                    await client.send_message(user_id, "Вы не состоите в группе.")
                    return

                link = await client.export_chat_invite_link(self.invited_chat_id)
                await client.send_message(user_id, f"Милости прошу к нашему шалашу: {link}")
            except Exception as e:
                logger.error(f"Произошла ошибка: {e}")
            await callback_query.answer()

class EventButton(BaseHandler):
    def __init__(self, app: Client, chat_id):
        super().__init__(app)
        self.chat_id = chat_id
        self.waiting_for_event_text = {}
        self.register_handlers()

    def register_handlers(self):
        @self.app.on_callback_query(filters.regex("event"))
        async def handle_event(callback_query):
            chat_id = callback_query.message.chat.id
            if chat_id != self.chat_id:
                await callback_query.answer("Эта функция работает только в группе.")
                return

            users = get_users_in_chat(chat_id)
            members = [f"@{username}" if username else full_name for username, full_name in users]
            mention_text = " ".join(members)

            await callback_query.message.reply_text("Введите текст для мероприятия:")
            self.waiting_for_event_text[callback_query.from_user.id] = {
                "chat_id": chat_id,
                "mention_text": mention_text
            }
            await callback_query.answer()

        @self.app.on_message(filters.text & filters.private)
        async def handle_event_text(client, message):
            if message.from_user.id in self.waiting_for_event_text:
                data = self.waiting_for_event_text.pop(message.from_user.id)
                chat_id = data["chat_id"]
                mention_text = data["mention_text"]

                event_text = message.text
                await client.send_message(chat_id, f"{mention_text}, {event_text}")

class DepartureHandler(BaseHandler):
    def __init__(self, app: Client, chat_id):
        super().__init__(app)
        self.chat_id = chat_id
        self.register_handlers()

    def register_handlers(self):
        @self.app.on_message(filters.text & filters.group)
        async def handle_departure(client, message):
            if message.text.lower() == "я уехал" and message.chat.id == self.chat_id:
                user_id = message.from_user.id
                try:
                    until_date = datetime.now() + timedelta(minutes=1)
                    await client.restrict_chat_member(
                        chat_id=self.chat_id,
                        user_id=user_id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=until_date
                    )
                    await client.send_message(
                        chat_id=self.chat_id,
                        text=f"Уважаемый {message.from_user.full_name} сообщил, что уехал, и был временно исключен из группы."
                    )
                    await client.send_message(
                        chat_id=user_id,
                        text="Вы были временно исключены из группы."
                    )
                except Exception as e:
                    logger.error(f"Произошла ошибка: {e}")

class MessageHandler(BaseHandler):
    def __init__(self, app: Client):
        super().__init__(app)
        self.register_handlers()

    def register_handlers(self):
        @self.app.on_message(filters.text)
        async def handle_message(message):
            user_id = message.from_user.id
            message_text = message.text

            # Добавляем сообщение в базу данных
            add_message(user_id, message_text)

class NewMemberHandler(BaseHandler):
    def __init__(self, app: Client):
        super().__init__(app)
        self.register_handlers()

    def register_handlers(self):
        @self.app.on_chat_join_request()
        async def handle_new_member(client, update):
            user = update.from_user
            chat_id = update.chat.id

            # Добавляем пользователя в базу данных
            add_user(
                user_id=user.id,
                username=user.username,
                full_name=user.first_name,
                chat_id=chat_id
            )
            logger.info(f"User {user.first_name} added to chat {chat_id}")

            # Приветствуем нового участника
            try:
                await client.send_message(chat_id, f"Приветствую, {user.first_name}! Добро пожаловать!")
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение в чат {chat_id}: {e}")

class ChatSelectionHandler(BaseHandler):
    def __init__(self, app: Client):
        super().__init__(app)
        self.register_handlers()

    def register_handlers(self):
        @self.app.on_message(filters.command("set_chats"))
        async def set_chats(message):
            try:
                inviting_chat_id, invited_chat_id = map(int, message.text.split()[1:])
                save_chat("INVITING_CHAT", inviting_chat_id)
                save_chat("INVITED_CHAT", invited_chat_id)

                update_chat_data(inviting_chat_id, invited_chat_id)

                await message.reply_text(
                    f"ID чатов установлены:\nINVITING_CHAT: {inviting_chat_id}\nINVITED_CHAT: {invited_chat_id}"
                )
            except (IndexError, ValueError):
                await message.reply_text("Используйте формат: /set_chats <inviting_chat_id> <invited_chat_id>")
