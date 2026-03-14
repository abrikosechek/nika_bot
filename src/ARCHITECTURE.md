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

Глобальные настройки:
- _god: ID god пользователя (глобальный, один для всех серверов)
- bananza_not_allowed: ID пользователя, которому запрещено использовать /bananza

Настройки сервера (по модулям):

{
  "_god": GOD_USER_ID,
  "bananza_not_allowed": USER_ID,
  "SERVER_ID": {
    "server_name": "server_name",
    "verification": {
      "unverif_role": ROLE_ID,
      "verif_role": ROLE_ID,
      "react_message_id": MESSAGE_ID
    },
    "fun": {
      "channel": CHANNEL_ID
    },
    "private_channels": {
      "category": CATEGORY_ID,
      "text_channel": CHANNEL_ID,
      "voice_channel": CHANNEL_ID
    }
  }
}

Поля модулей:

**verification** (модуль VerificationModule):
- unverif_role: роль для новых участников
- verif_role: роль после верификации
- react_message_id: сообщение для реакции верификации

**fun** (модуль RollModule):
- channel: канал для команды /roll

**private_channels** (модуль PrivateModule):
- category: категория для приватных каналов
- text_channel: текстовый канал для команд управления
- voice_channel: голосовой канал создания (плюсик)

Тестовый режим:
- Если в .env IS_TEST=true, используется config/test_guilds.json
- Если IS_TEST=false (по умолчанию), используется config/guilds.json

Команды модуля god
==================

God пользователь настраивается только через файл config/guilds.json (поле _god).
Бот следует за god пользователем по всем голосовым каналам на всех серверах.


Команды модуля private_channels
===============================

Настройка только через config/guilds.json (вручную):

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
