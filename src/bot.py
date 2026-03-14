import asyncio
import os
import signal
import sys
import logging

import discord
from discord import LoginFailure
from discord.ext import commands
from dotenv import load_dotenv

from src.core import Module
from src.modules import ALL_MODULES
from src.utils.config import config
from src.utils.checks import ChannelCheckError
from src.utils.db import db

# Включаем UTF-8 для Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Перезагружаем кэш конфигурации после загрузки .env
config.reload()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.reactions = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Реестр загруженных модулей
_loaded_modules: list[Module] = []


async def load_modules() -> None:
    """Загрузка всех модулей"""
    for module_class in ALL_MODULES:
        try:
            module = module_class(bot)
            
            # Получаем список команд до регистрации
            commands_before = len(bot.tree.get_commands())
            
            await module.setup()
            
            # Получаем список команд после регистрации
            commands_after = len(bot.tree.get_commands())
            registered_count = commands_after - commands_before
            
            _loaded_modules.append(module)
            print(f'✅ Модуль загружен: {module.name}')
            if registered_count > 0:
                commands_list = bot.tree.get_commands()
                for cmd in commands_list[-registered_count:]:
                    print(f'   └─ ⚡ /{cmd.name}')
        except Exception as e:
            logger.error(f'❌ Ошибка загрузки модуля {module_class.__name__}: {e}', exc_info=True)


@bot.event
async def on_ready():
    print(f'Бот готов! {bot.user}')
    print(f'Подключён к {len(bot.guilds)} серверам')

    # Подключение к базе данных
    await db.connect()
    print('🗄️ База данных подключена')

    # Загрузка модулей
    if not _loaded_modules:
        await load_modules()

    # Синхронизация slash-команд
    await bot.tree.sync()
    print('Slash-команды синхронизированы')

    # Вызов on_ready для всех модулей
    for module in _loaded_modules:
        await module.on_ready()


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: discord.app_commands.AppCommandError
) -> None:
    """Глобальный обработчик ошибок slash команд"""
    if isinstance(error, ChannelCheckError):
        await interaction.response.send_message(
            error.message,
            ephemeral=True
        )
    elif isinstance(error, commands.CommandNotFound):
        logger.warning(f'Command not found: {interaction.command_name}')
    elif isinstance(error, commands.MissingPermissions):
        await interaction.response.send_message(
            '❌ Недостаточно прав для выполнения команды.',
            ephemeral=True
        )
    elif isinstance(error, commands.BotMissingPermissions):
        await interaction.response.send_message(
            '❌ У бота недостаточно прав для выполнения команды.',
            ephemeral=True
        )
    elif isinstance(error, commands.CommandOnCooldown):
        await interaction.response.send_message(
            f'⏳ Команда на перезарядке. Попробуйте через {error.retry_after:.1f} сек.',
            ephemeral=True
        )
    else:
        cmd_name = interaction.command.name if interaction.command else 'unknown'
        logger.error(
            f'Ошибка команды {cmd_name}: {error}',
            exc_info=error
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(
                '❌ Произошла ошибка при выполнении команды.',
                ephemeral=True
            )


@bot.event
async def on_error(event: str, *args, **kwargs) -> None:
    """Глобальный обработчик ошибок для view кнопок"""
    logger.error(f'Ошибка в событии {event}: {args}', exc_info=True)


@bot.event
async def on_member_join(member: discord.Member):
    for module in _loaded_modules:
        try:
            await module.on_member_join(member)
        except Exception as e:
            logger.error(f'Ошибка в модуле {module.name}.on_member_join: {e}', exc_info=True)


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    for module in _loaded_modules:
        try:
            await module.on_raw_reaction_add(payload)
        except Exception as e:
            logger.error(f'Ошибка в модуле {module.name}.on_raw_reaction_add: {e}', exc_info=True)


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    for module in _loaded_modules:
        try:
            await module.on_raw_reaction_remove(payload)
        except Exception as e:
            logger.error(f'Ошибка в модуле {module.name}.on_raw_reaction_remove: {e}', exc_info=True)


@bot.event
async def on_guild_join(guild: discord.Guild):
    print(f'Добавлен на сервер: {guild.name} (ID: {guild.id})')
    for module in _loaded_modules:
        try:
            await module.on_guild_join(guild)
        except Exception as e:
            logger.error(f'Ошибка в модуле {module.name}.on_guild_join: {e}', exc_info=True)


@bot.event
async def on_guild_remove(guild: discord.Guild):
    print(f'Удалён с сервера: {guild.name} (ID: {guild.id})')
    for module in _loaded_modules:
        try:
            await module.on_guild_remove(guild)
        except Exception as e:
            logger.error(f'Ошибка в модуле {module.name}.on_guild_remove: {e}', exc_info=True)


@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState
):
    for module in _loaded_modules:
        try:
            await module.on_voice_state_update(member, before, after)
        except Exception as e:
            logger.error(f'Ошибка в модуле {module.name}.on_voice_state_update: {e}', exc_info=True)


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    """Глобальный обработчик ошибок префикс команд"""
    if isinstance(error, commands.CommandNotFound):
        logger.warning(f'Command not found: {ctx.command}')
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ Недостаточно прав для выполнения команды.', delete_after=5)
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send('❌ У бота недостаточно прав для выполнения команды.', delete_after=5)
    else:
        logger.error(f'Ошибка команды {ctx.command}: {error}', exc_info=error)


@bot.event
async def on_close():
    """Закрытие подключения к базе данных при остановке бота"""
    await db.close()
    logger.info('🗄️ База данных отключена')


def run():
    """Запуск бота с обработкой Ctrl+C"""
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error('❌ Токен бота не найден в .env')
        return
    
    try:
        bot.run(token)
    except KeyboardInterrupt:
        logger.info('🛑 Получен сигнал остановки')
    except discord.LoginFailure:
        logger.error('❌ Ошибка авторизации. Проверьте токен в .env')
    except Exception as e:
        logger.error(f'❌ Ошибка запуска: {e}')
    finally:
        # Закрытие ресурсов в синхронном контексте
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(cleanup())
        finally:
            loop.close()
        logger.info('✅ Бот остановлен')


async def cleanup():
    """Очистка ресурсов при остановке"""
    await db.close()
    logger.info('🗄️ База данных отключена')
