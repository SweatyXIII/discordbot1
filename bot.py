import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import asyncio
import time
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

# Список сервисов для проверки
SERVICES = {
    "Steam": ("https://store.steampowered.com", "steam"),
    "Epic Games Store": ("https://www.epicgames.com", "epic"),
    "Ubisoft Connect": ("https://ubisoftconnect.com", "ubisoft"),
    "YouTube": ("https://www.youtube.com", "youtube"),
    "Discord": ("https://discord.com", "discord"),
    "Telegram": ("https://web.telegram.org", "telegram"),
    "Battle.net": ("https://eu.shop.battle.net", "battlenet"),
    "Riot Games": ("https://www.riotgames.com", "riot")
}

class ServerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
    
    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Бот {self.user} запущен и готов к работе!")

bot = ServerBot()

async def check_service(url, name):
    """Проверяет доступность сервиса"""
    try:
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5, allow_redirects=True) as response:
                latency = round((time.time() - start_time) * 1000)
                
                if response.status == 200:
                    return True, latency, "OK"
                else:
                    return False, latency, f"HTTP {response.status}"
    except asyncio.TimeoutError:
        return False, None, "Таймаут"
    except aiohttp.ClientConnectorError:
        return False, None, "Нет соединения"
    except Exception as e:
        return False, None, str(e)[:30]

@bot.tree.command(name="check", description="Проверить доступность игровых сервисов")
async def check_command(interaction: discord.Interaction):
    await interaction.response.defer()
    
    start_total = time.time()
    
    embed = discord.Embed(
        title="🔍 ПРОВЕРКА ДОСТУПНОСТИ СЕРВИСОВ",
        description="Проверяю подключение к серверам...",
        color=0x3498db,
        timestamp=datetime.now()
    )
    
    message = await interaction.followup.send(embed=embed)
    
    results = []
    
    for service_name, (url, tag) in SERVICES.items():
        embed.description = f"🔄 Проверяю {service_name}..."
        await message.edit(embed=embed)
        
        is_online, latency, error_msg = await check_service(url, service_name)
        
        if is_online:
            icon = "✅"
            status = f"доступен ({latency} мс)"
        else:
            icon = "❌"
            status = f"НЕ ДОСТУПЕН ({error_msg})"
        
        results.append(f"{icon} **{service_name}** — {status}")
    
    total_time = round((time.time() - start_total), 1)
    
    embed = discord.Embed(
        title="🔍 ПРОВЕРКА ДОСТУПНОСТИ СЕРВИСОВ",
        description="\n".join(results),
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"⏱ Проверка завершена за {total_time} сек")
    
    await message.edit(embed=embed)

@bot.tree.command(name="checklink", description="Проверить доступность любой ссылки")
@app_commands.describe(url="Ссылка для проверки (например, https://google.com)")
async def checklink_command(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    
    # Добавляем https:// если нет протокола
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5, allow_redirects=True, ssl=False) as response:
                latency = round((time.time() - start_time) * 1000)
                
                if response.status < 300:
                    status_emoji = "✅"
                    color = 0x00ff00
                elif response.status < 400:
                    status_emoji = "🟡"
                    color = 0xffaa00
                else:
                    status_emoji = "❌"
                    color = 0xff0000
                
                content_length = response.headers.get('Content-Length', 'неизвестно')
                if content_length != 'неизвестно':
                    try:
                        size_kb = int(content_length) / 1024
                        size_info = f"{size_kb:.1f} KB"
                    except:
                        size_info = content_length
                else:
                    size_info = "неизвестно"
                
                embed = discord.Embed(
                    title=f"{status_emoji} Результат проверки",
                    color=color,
                    timestamp=datetime.now()
                )
                embed.add_field(name="URL", value=f"```{url[:100]}```", inline=False)
                embed.add_field(name="Статус", value=f"HTTP {response.status} {response.reason}", inline=True)
                embed.add_field(name="Задержка", value=f"{latency} мс", inline=True)
                embed.add_field(name="Размер", value=size_info, inline=True)
                
                headers = dict(response.headers.items())
                important_headers = {k: v for k, v in headers.items() 
                                   if k.lower() in ['server', 'content-type', 'last-modified']}
                if important_headers:
                    headers_text = "\n".join([f"**{k}:** {v}" for k, v in important_headers.items()])
                    embed.add_field(name="📋 Заголовки", value=headers_text, inline=False)
                
    except asyncio.TimeoutError:
        embed = discord.Embed(
            title="⏰ Таймаут",
            description=f"Сервер {url} не ответил за 5 секунд",
            color=0xff0000,
            timestamp=datetime.now()
        )
    except aiohttp.ClientConnectorError as e:
        embed = discord.Embed(
            title="🔌 Ошибка подключения",
            description=f"Не удалось подключиться к {url}\n```{str(e)[:100]}```",
            color=0xff0000,
            timestamp=datetime.now()
        )
    except Exception as e:
        embed = discord.Embed(
            title="❌ Ошибка",
            description=f"```{str(e)[:100]}```",
            color=0xff0000,
            timestamp=datetime.now()
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="check_service", description="Проверить конкретный сервис")
@app_commands.describe(service="Название сервиса для проверки")
async def check_service_command(interaction: discord.Interaction, service: str):
    await interaction.response.defer()
    
    service_lower = service.lower()
    found = None
    
    for name, (url, tag) in SERVICES.items():
        if service_lower in name.lower() or service_lower == tag:
            found = (name, url)
            break
    
    if not found:
        services_list = "\n".join([f"• {name} (`{tag}`)" for name, (_, tag) in SERVICES.items()])
        embed = discord.Embed(
            title="❌ Сервис не найден",
            description=f"Доступные сервисы:\n{services_list}",
            color=0xff0000
        )
        await interaction.followup.send(embed=embed)
        return
    
    name, url = found
    is_online, latency, error_msg = await check_service(url, name)
    
    if is_online:
        embed = discord.Embed(
            title=f"✅ {name} доступен",
            description=f"Задержка: {latency} мс\nСтатус: OK",
            color=0x00ff00
        )
    else:
        embed = discord.Embed(
            title=f"❌ {name} НЕ ДОСТУПЕН",
            description=f"Ошибка: {error_msg}",
            color=0xff0000
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="ping", description="Проверить задержку бота")
async def ping_command(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Понг!",
        description=f"Задержка бота: {latency} мс",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Показать список команд")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 Доступные команды",
        description="""
        **/check** — проверить все игровые сервисы
        **/checklink [ссылка]** — проверить любую ссылку
        **/check_service [название]** — проверить конкретный сервис
        **/ping** — проверить задержку бота
        **/help** — показать это сообщение
        """,
        color=0x3498db
    )
    embed.add_field(
        name="🔍 Игровые сервисы", 
        value="Steam, Epic Games Store, Ubisoft Connect, YouTube, Discord, Telegram, Battle.net, Riot Games"
    )
    embed.add_field(
        name="🔗 Примеры checklink",
        value="`/checklink google.com`\n`/checklink https://github.com`\n`/checklink 1.1.1.1`",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    print(f"🤖 {bot.user} подключился к Discord!")
    print(f"📡 Серверов: {len(bot.guilds)}")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="/check | /checklink"
        )
    )

@bot.command(name="help")
async def help_text_command(ctx):
    embed = discord.Embed(
        title="🤖 SERVER MONITOR BOT",
        description="Бот для проверки доступности серверов и сайтов",
        color=0x5865F2
    )
    
    embed.add_field(
        name="📋 **Команды**",
        value=(
            "`/help` - Показать это сообщение\n"
            "`/ping` - Проверить задержку бота\n"
            "`/check` - Проверить все игровые сервисы\n"
            "`/check_service [название]` - Проверить конкретный сервис\n"
            "`/checklink [url]` - Проверить любую ссылку"
        ),
        inline=False
    )
    
    await ctx.send(embed=embed)

if __name__ == "__main__":
    bot.run(TOKEN)
