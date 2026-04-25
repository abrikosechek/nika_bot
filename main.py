import os
import pathlib
from dotenv import load_dotenv
import discord
from discord.ext import commands

load_dotenv()

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)


async def load_cogs():
    cog_folder = pathlib.Path("cogs")
    
    for file in cog_folder.glob("*.py"):
        if file.name.startswith("_"):
            continue

        module_name = f"cogs.{file.stem}"

        try:
            await bot.load_extension(module_name)
            print(f"✅ Загружен модуль: {file.stem}")
        except Exception as e:
            print(f"❌ Ошибка загрузки модуля {file.stem}: {e}")


@bot.event
async def on_ready():
    await load_cogs()

# load commands
    try:
        await bot.tree.sync()
        print("✅ Команды синхронизированы")
    except Exception as e:
        print(f"❌ Ошибка синхронизации: {e}")

    print("Bot is running!")


if __name__ == "__main__":
    TOKEN = os.getenv("SECRET")

    if not TOKEN:
        print("❌ Токен не найден!")
    else:
        bot.run(TOKEN)
