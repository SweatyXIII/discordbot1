import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io
import random
import aiohttp
import os
from dotenv import load_dotenv
from collections import deque
import datetime
from threading import Thread
from flask import Flask

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

# Flask app для Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Demotivator Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Запускаем Flask в фоне
flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()

# Хранилище сообщений (последние 500)
message_history = deque(maxlen=500)

class DemotivatorBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        super().__init__(command_prefix='v1!', intents=intents)
    
    async def setup_hook(self):
        await self.tree.sync()
        print(f"Бот {self.user} запущен!")

bot = DemotivatorBot()

async def download_random_image():
    """Скачивает случайную картинку"""
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://picsum.photos/1024/768"
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    img_data = await resp.read()
                    img = Image.open(io.BytesIO(img_data))
                    return img.resize((1024, 768))
    except:
        return None

def get_font(size, bold=False):
    """Пытается найти шрифт с поддержкой русского"""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "arial.ttf"
    ]
    
    if bold:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "arialbd.ttf"
        ]
    
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    
    return ImageFont.load_default()

def create_demotivator(text, author_name, background_img=None):
    """Создаёт демотиватор с уменьшенным на 30% текстом"""
    width, height = 1200, 1000
    img_width, img_height = 1000, 600
    
    canvas = Image.new('RGB', (width, height), color=(0, 0, 0))
    
    if background_img:
        bg_resized = background_img.resize((img_width, img_height))
        canvas.paste(bg_resized, ((width - img_width)//2, 120))
    else:
        # Градиент
        for i in range(img_height):
            color = int(50 + (i / img_height) * 100)
            draw_temp = ImageDraw.Draw(canvas)
            draw_temp.rectangle(
                [(width - img_width)//2, 120 + i, (width + img_width)//2, 120 + i + 1],
                fill=(color, color, color)
            )
    
    draw = ImageDraw.Draw(canvas)
    
    # Рамка вокруг картинки
    frame_x = (width - img_width)//2 - 5
    frame_y = 115
    draw.rectangle(
        [frame_x, frame_y, frame_x + img_width + 10, frame_y + img_height + 10],
        outline=(255, 255, 255),
        width=4
    )
    
    # Оригинальное сообщение сверху (уменьшено)
    original_font = get_font(18)  # Было 24
    original_text = text
    bbox_orig = draw.textbbox((0, 0), original_text, font=original_font)
    orig_width = bbox_orig[2] - bbox_orig[0]
    x_orig = (width - orig_width) // 2
    y_orig = 40
    
    for offset in [(-1,-1), (1,-1), (-1,1), (1,1)]:
        draw.text((x_orig + offset[0], y_orig + offset[1]), original_text, font=original_font, fill=(0,0,0))
    draw.text((x_orig, y_orig), original_text, font=original_font, fill=(200, 200, 200))
    
    # Основной текст (УМЕНЬШЕН НА 30%)
    words = text.split()
    word_count = len(words)
    
    # НОВЫЕ РАЗМЕРЫ (уменьшены на 30% от предыдущих)
    if word_count <= 2:
        font_size = 49      # Было 70
    elif word_count <= 3:
        font_size = 42      # Было 60
    elif word_count <= 4:
        font_size = 38      # Было 55
    else:
        font_size = 34      # Было 48
    
    font_big = get_font(font_size, bold=True)
    font_small = get_font(16)  # Для автора
    
    # Разбиваем на строки
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        if len(current_line) >= 3 or len(' '.join(current_line)) > 20:
            lines.append(' '.join(current_line))
            current_line = []
    
    if current_line:
        lines.append(' '.join(current_line))
    
    final_text = '\n'.join(lines)
    
    # Центрируем основной текст
    bbox = draw.multiline_textbbox((0, 0), final_text, font=font_big, align="center")
    text_width = bbox[2] - bbox[0]
    
    x = (width - text_width) // 2
    y = height - 180  # Поднял повыше
    
    # Обводка (поменьше)
    for offset in [(-2,-2), (2,-2), (-2,2), (2,2)]:
        draw.multiline_text(
            (x + offset[0], y + offset[1]), 
            final_text, 
            font=font_big, 
            fill=(0, 0, 0),
            align="center"
        )
    
    # Белый текст
    draw.multiline_text(
        (x, y), 
        final_text, 
        font=font_big, 
        fill=(255, 255, 255),
        align="center"
    )
    
    # Автор снизу
    author_footer = f"— {author_name}"
    bbox_author = draw.textbbox((0, 0), author_footer, font=font_small)
    author_width = bbox_author[2] - bbox_author[0]
    x_author = (width - author_width) // 2
    y_author = y + 60
    
    for offset in [(-1,-1), (1,-1), (-1,1), (1,1)]:
        draw.text((x_author + offset[0], y_author + offset[1]), author_footer, font=font_small, fill=(0,0,0))
    draw.text((x_author, y_author), author_footer, font=font_small, fill=(180,180,180))
    
    return canvas

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Сохраняем сообщения от 1 до 6 слов
    if message.content and not message.content.startswith('v1!'):
        words = message.content.strip().split()
        word_count = len(words)
        
        if 1 <= word_count <= 6:
            message_history.append({
                'text': message.content.upper(),
                'author': message.author.display_name,
                'time': datetime.datetime.now(),
                'words': word_count
            })
            print(f"Добавлено ({word_count} слов): {message.content[:30]}... (всего: {len(message_history)})")
    
    await bot.process_commands(message)

@bot.command(name="dem")
async def dem_command(ctx):
    """Создать демотиватор из случайного сообщения"""
    
    if len(message_history) == 0:
        await ctx.send("В истории пока нет сообщений. Напиши что-нибудь (1-6 слов).")
        return
    
    async with ctx.typing():
        msg_data = random.choice(list(message_history))
        
        bg = await download_random_image()
        img = create_demotivator(msg_data['text'], msg_data['author'], bg)
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        file = discord.File(img_buffer, filename='demotivator.png')
        await ctx.send(file=file)

@bot.command(name="dem_last")
async def dem_last_command(ctx):
    """Показать последние сообщения"""
    if len(message_history) == 0:
        await ctx.send("История пуста")
        return
    
    last_messages = list(message_history)[-10:]
    
    embed = discord.Embed(
        title="Последние сообщения",
        color=0x3498db
    )
    
    for msg in reversed(last_messages):
        embed.add_field(
            name=f"{msg['author']} ({msg['words']} сл.)",
            value=msg['text'][:50],
            inline=False
        )
    
    embed.set_footer(text=f"Всего: {len(message_history)} сообщений")
    await ctx.send(embed=embed)

@bot.command(name="dem_stats")
async def dem_stats_command(ctx):
    """Статистика"""
    embed = discord.Embed(
        title="Статистика",
        color=0x00ff00
    )
    embed.add_field(name="Сообщений в базе", value=str(len(message_history)), inline=True)
    
    if message_history:
        # Распределение по длине
        word_dist = {}
        for msg in message_history:
            word_dist[msg['words']] = word_dist.get(msg['words'], 0) + 1
        
        dist_text = "\n".join([f"{w} слов: {c}" for w, c in sorted(word_dist.items())])
        embed.add_field(name="Распределение", value=dist_text, inline=True)
        
        # Топ авторы
        authors = {}
        for msg in message_history:
            authors[msg['author']] = authors.get(msg['author'], 0) + 1
        
        top = sorted(authors.items(), key=lambda x: x[1], reverse=True)[:3]
        top_text = "\n".join([f"{a}: {c}" for a, c in top])
        embed.add_field(name="Топ авторов", value=top_text, inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="dem_help")
async def dem_help_command(ctx):
    """Помощь"""
    embed = discord.Embed(
        title="ДЕМОТИВАТОР БОТ",
        description="Превращает короткие сообщения (1-6 слов) в демотиваторы",
        color=0xff5500
    )
    embed.add_field(
        name="Команды",
        value=(
            "dem - случайный демотиватор\n"
            "dem_last - последние сообщения\n"
            "dem_stats - статистика\n"
            "dem_help - помощь"
        ),
        inline=False
    )
    embed.set_footer(text="Пиши коротко и ясно")
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Бот {bot.user} готов!")
    print(f"Сохраняю сообщения от 1 до 6 слов")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="чат | v1!dem"
        )
    )

if __name__ == "__main__":
    bot.run(TOKEN)
