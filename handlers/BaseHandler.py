from pyrogram import Client

class BaseHandler:
    def __init__(self, app: Client):
        self.app = app

    def register_handlers(self):
        raise NotImplementedError("Метод register_handlers должен быть переопределен в дочернем классе.")