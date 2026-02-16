import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import io
import random
import aiohttp
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

# Хранилище фраз
phrases = [
    "ЖИЗНЬ",
    "СДЕЛАЛ ДЕЛО - ГУЛЯЙ СМЕЛО",
    "КОГДА ПРОСНУЛСЯ А ВЫХОДНОЙ",
    "ПОНЕДЕЛЬНИК",
    "КОФЕ - ЭТО ЖИДКАЯ ВАЛЮТА",
    "ПОЧЕМУ НЕ СПИШЬ? РАБОТАЙ!"
]

# Список источников картинок
IMAGE_SOURCES = [
    "https://picsum.photos/800/600",  # Random photos
    "https://picsum.photos/800/600?grayscale",
    "https://picsum.photos/800/600?blur"
]

class DemotivatorBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        super().__init__(command_prefix=['!', 'v1!'], intents=intents)
    
    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Бот {self.user} запущен!")
        print(f"📡 Фраз в базе: {len(phrases)}")

bot = DemotivatorBot()

async def download_random_image():
    """
    Скачивает случайную картинку из интернета
    """
    url = random.choice(IMAGE_SOURCES)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    image_data = await response.read()
                    img = Image.open(io.BytesIO(image_data))
                    # Изменяем размер для демотиватора
                    img = img.resize((800, 600), Image.Resampling.LANCZOS)
                    return img
                else:
                    print(f"Ошибка загрузки: {response.status}")
                    return None
    except Exception as e:
        print(f"Ошибка при загрузке картинки: {e}")
        return None

def create_demotivator_with_image(text, background_img):
    """
    Создаёт демотиватор с фоном из скачанной картинки
    """
    # Создаём холст для демотиватора (с рамкой)
    width, height = 900, 700
    canvas = Image.new('RGB', (width, height), color=(0, 0, 0))
    
    # Вставляем картинку в центр с отступами
    img_x = (width - 800) // 2
    img_y = 50
    canvas.paste(background_img, (img_x, img_y))
    
    # Рисуем белую рамку вокруг картинки
    draw = ImageDraw.Draw(canvas)
    draw.rectangle(
        [img_x-2, img_y-2, img_x+802, img_y+602],
        outline=(255, 255, 255),
        width=3
    )
    
    # Пробуем загрузить шрифты
    try:
        font_big = ImageFont.truetype("arial.ttf", 48)
        font_small = ImageFont.truetype("arial.ttf", 24)
    except:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Разбиваем текст на строки
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        if len(' '.join(current_line)) > 20:
            current_line.pop()
            lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    # Определяем верхний и нижний текст
    if len(lines) >= 2:
        upper_text = lines[0]
        lower_text = ' '.join(lines[1:])
    else:
        upper_text = text
        lower_text = " "
    
    # Рисуем верхний текст (большой, белый)
    bbox = draw.textbbox((0, 0), upper_text, font=font_big)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (width - text_width) // 2
    y = img_y + 620
    
    # Обводка для верхнего текста
    for offset in [(-2,-2), (2,-2), (-2,2), (2,2)]:
        draw.text((x+offset[0], y+offset[1]), upper_text, font=font_big, fill=(0,0,0))
    draw.text((x, y), upper_text, font=font_big, fill=(255,255,255))
    
    # Рисуем нижний текст (маленький, серый)
    if lower_text.strip():
        bbox_small = draw.textbbox((0, 0), lower_text, font=font_small)
        text_width_small = bbox_small[2] - bbox_small[0]
        
        x_small = (width - text_width_small) // 2
        y_small = y + 50
        
        for offset in [(-1,-1), (1,-1), (-1,1), (1,1)]:
            draw.text((x_small+offset[0], y_small+offset[1]), lower_text, font=font_small, fill=(0,0,0))
        draw.text((x_small, y_small), lower_text, font=font_small, fill=(200,200,200))
    
    return canvas

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Сохраняем сообщения в базу
    if not message.content.startswith('!'):
        msg = message.content.strip().upper()[:50]
        if len(msg) > 5:
            phrases.append(msg)
            if len(phrases) > 1000:
                phrases.pop(0)
            print(f"📝 Добавлена фраза: {msg} (всего: {len(phrases)})")
    
    await bot.process_commands(message)

@bot.command(name="dem")
async def demotivator_command(ctx, *, text=None):
    """Создать демотиватор из текста или случайной фразы (с картинкой из интернета)"""
    async with ctx.typing():
        # Определяем текст
        if text:
            phrase = text.upper()
        else:
            if phrases:
                phrase = random.choice(phrases)
            else:
                phrase = "НЕТ ФРАЗ В БАЗЕ"
        
        # Отправляем статус
        status_msg = await ctx.send("🔄 Загружаю картинку из интернета...")
        
        # Скачиваем случайную картинку
        background = await download_random_image()
        
        if background:
            await status_msg.edit(content="🖼️ Создаю демотиватор...")
            # Создаём демотиватор с картинкой
            img = create_demotivator_with_image(phrase, background)
        else:
            await status_msg.edit(content="⚠️ Не удалось загрузить картинку, делаю чёрный фон...")
            # Если не удалось скачать - делаем с чёрным фоном
            img = Image.new('RGB', (900, 700), color=(20, 20, 20))
            draw = ImageDraw.Draw(img)
            draw.rectangle([(50, 50), (850, 550)], outline=(255, 255, 255), width=3)
            
            # Простой текст для чёрного фона
            try:
                font = ImageFont.truetype("arial.ttf", 60)
            except:
                font = ImageFont.load_default()
            
            bbox = draw.textbbox((0, 0), phrase, font=font)
            text_width = bbox[2] - bbox[0]
            x = (900 - text_width) // 2
            y = 300
            
            draw.text((x, y), phrase, font=font, fill=(255,255,255))
        
        # Сохраняем в буфер
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Удаляем статус
        await status_msg.delete()
        
        # Отправляем результат
        file = discord.File(img_buffer, filename='demotivator.png')
        await ctx.send(f"**{phrase}**", file=file)

@bot.command(name="dem_help")
async def dem_help_command(ctx):
    """Помощь по демотиватору"""
    embed = discord.Embed(
        title="🎭 Демотиватор Бот",
        description="Создаёт демотиваторы из сообщений в чате со случайными картинками из интернета",
        color=0x00ff00
    )
    embed.add_field(
        name="Команды",
        value=(
            "`!dem` - Случайный демотиватор из базы\n"
            "`!dem [текст]` - Демотиватор с твоим текстом\n"
            "`!dem_stats` - Статистика фраз\n"
            "`!dem_help` - Это сообщение"
        ),
        inline=False
    )
    embed.add_field(
        name="🌐 Картинки",
        value=(
            "Бот скачивает случайные фото с **picsum.photos**\n"
            "Если картинка не грузится - делает чёрный фон"
        ),
        inline=False
    )
    await ctx.send(embed=embed)

@bot.command(name="dem_stats")
async def dem_stats_command(ctx):
    """Статистика базы фраз"""
    embed = discord.Embed(
        title="📊 Статистика демотиватора",
        color=0x3498db
    )
    embed.add_field(name="Всего фраз", value=str(len(phrases)), inline=True)
    
    if phrases:
        # Последние 5 фраз
        last_phrases = "\n".join([f"• {p}" for p in phrases[-5:]])
        embed.add_field(name="Последние фразы", value=last_phrases, inline=False)
    
    embed.add_field(
        name="🌐 Источник картинок",
        value="picsum.photos (случайные фото)",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"🤖 {bot.user} подключился!")
    print(f"📡 Серверов: {len(bot.guilds)}")
    print(f"💬 Фраз в базе: {len(phrases)}")
    print(f"🌐 Источник картинок: picsum.photos")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="!dem | Картинки из сети"
        )
    )

if __name__ == "__main__":
    bot.run(TOKEN)