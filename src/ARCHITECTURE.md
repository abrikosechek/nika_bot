"""
Архитектура бота
================

Структура проекта
-----------------

src/
├── core/           # Ядро: базовые классы и интерфейсы
│   ├── __init__.py
│   ├── module.py   # Базовый класс Module (ABC)
│   └── service.py  # Базовый класс Service (ABC)
│
├── modules/        # Модули бота (функциональные блоки)
│   ├── __init__.py # Реестр всех модулей
│   ├── fun/        # Развлекательные команды
│   │   ├── __init__.py
│   │   └── roll.py
│   ├── verification/  # Верификация участников
│   │   ├── __init__.py
│   │   └── verification.py
│   ├── god/        # God mode (бот следует за пользователем)
│   │   ├── __init__.py
│   │   └── follower.py
│   └── private_channels/  # Приватные голосовые каналы
│       ├── __init__.py
│       └── private.py
│
├── services/       # Переиспользуемые сервисы
│   ├── __init__.py
│   └── voice.py    # VoiceService для управления голосом
│
├── utils/          # Утилиты (хранилище, конфиги)
│   ├── __init__.py
│   ├── config.py   # ConfigCache для кэширования guilds.json
│   └── storage.py  # Функции для работы с данными
│
├── ui/             # UI компоненты
│   ├── __init__.py
│   └── bananza.py  # Embed для слот-машины
│
├── __init__.py
├── bot.py          # Точка входа, загрузчик модулей
└── ARCHITECTURE.md # Документация


Добавление нового модуля
========================

1. Создайте папку модуля: src/modules/<module_name>/
2. Создайте файл с классом модуля:

   from src.core import Module
   import discord
   from discord.ext import commands

   class MyModule(Module):
       name = "my_module"
       description = "Описание модуля"
       
       async def setup(self) -> None:
           @self.bot.tree.command(name='cmd', description='Описание')
           async def cmd(interaction: discord.Interaction):
               await interaction.response.send_message('Hello!')

3. Добавьте импорт в src/modules/__init__.py:
   
   from src.modules.my_module import MyModule
   
   ALL_MODULES = [
       ...,
       MyModule,
   ]

4. Готово! Модуль загрузится автоматически.


Структура guilds.json
=====================

{
  "_god": GOD_USER_ID,
  "bananza_not_allowed": USER_ID,
  "SERVER_ID": {
    "server_name": "server_name",
    "roles": {
      "unverif_role": ROLE_ID,
      "verif_role": ROLE_ID
    },
    "messages": {
      "react_verif_message_id": MESSAGE_ID
    },
    "channels": {
      "fun_channel": CHANNEL_ID,
      "private_category": CATEGORY_ID,
      "private_text_channel": TEXT_CHANNEL_ID,
      "private_voice_channel": VOICE_CHANNEL_ID
    }
  }
}

Поля:
- _god: ID god пользователя (глобальный, один для всех серверов)
- bananza_not_allowed: ID пользователя, которому запрещено использовать /bananza
- SERVER_ID.server_name: название сервера
- SERVER_ID.roles.unverif_role: роль для новых участников
- SERVER_ID.roles.verif_role: роль после верификации
- SERVER_ID.messages.react_verif_message_id: сообщение для реакции верификации
- SERVER_ID.channels.fun_channel: канал для команды /roll
- SERVER_ID.channels.private_category: категория для приватных каналов
- SERVER_ID.channels.private_text_channel: текстовый канал управления (шестерёнка)
- SERVER_ID.channels.private_voice_channel: голосовой канал создания (плюсик)

Команды модуля god
==================

God пользователь настраивается только через файл data/guilds.json (поле _god).
Бот следует за god пользователем по всем голосовым каналам на всех серверах.


Команды модуля private_channels
===============================

Настройка только через data/guilds.json (вручную):

{
  "SERVER_ID": {
    "channels": {
      "private_category": CATEGORY_ID,
      "private_voice_channel": VOICE_CHANNEL_ID
    }
  }
}

Команды:
/close - Закрыть (удалить) свой приватный канал
/lock - 🔒 Заблокировать вход в приватный канал
/unlock - 🔓 Разблокировать вход в приватный канал

Логика работы:
- Пользователь заходит в "private_voice_channel" → создаётся канал с его ником
- Если все вышли из приватного канала → канал удаляется
- У пользователя только один приватный канал одновременно
- При повторном заходе в "создать" → перемещается в существующий канал
- /lock меняет название на 🔒 и запрещает вход @everyone
- /unlock меняет название на 🔓 и разрешает вход


Обработка ошибок
================

Все ошибки обрабатываются глобально:
- on_app_command_error - ошибки slash команд
- on_command_error - ошибки префикс команд
- Обработчики в событиях модулей - ошибки в on_* методах

Ошибки логируются с exc_info=True для полного стектрейса.
