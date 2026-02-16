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

def wrap_text(text, font, draw, max_width):
    """Разбивает текст на строки по ширине"""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        temp_line = ' '.join(current_line)
        bbox = draw.textbbox((0, 0), temp_line, font=font)
        if bbox[2] - bbox[0] > max_width:
            current_line.pop()
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def create_demotivator(header_text, main_text, background_img=None):
    """Создаёт демотиватор с заголовком и основным текстом одинакового размера"""
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
    
    # Определяем размер шрифта на основе длины основного текста
    main_words = main_text.split()
    word_count = len(main_words)
    
    if word_count <= 2:
        font_size = 70
    elif word_count <= 4:
        font_size = 60
    elif word_count <= 6:
        font_size = 50
    elif word_count <= 10:
        font_size = 45
    elif word_count <= 15:
        font_size = 38
    else:
        font_size = 32
    
    # Шрифт для всего (одинаковый размер)
    font_main = get_font(font_size, bold=True)
    
    # Максимальная ширина текста (с учетом отступов)
    max_text_width = width - 100
    
    # Разбиваем заголовок на строки
    header_lines = wrap_text(header_text, font_main, draw, max_text_width)
    header_final = '\n'.join(header_lines)
    
    # Разбиваем основной текст на строки
    main_lines = wrap_text(main_text, font_main, draw, max_text_width)
    main_final = '\n'.join(main_lines)
    
    # ОТСТУПЫ - одинаковые для обоих текстов
    header_y = 50  # Отступ заголовка от верхнего края
    main_y = height - 250  # Отступ основного текста от нижнего края
    
    # Рисуем заголовок (белый)
    bbox_header = draw.multiline_textbbox((0, 0), header_final, font=font_main, align="center")
    header_width = bbox_header[2] - bbox_header[0]
    x_header = (width - header_width) // 2
    
    # Обводка для заголовка
    for offset in [(-2,-2), (2,-2), (-2,2), (2,2)]:
        draw.multiline_text(
            (x_header + offset[0], header_y + offset[1]), 
            header_final, 
            font=font_main, 
            fill=(0, 0, 0),
            align="center"
        )
    
    draw.multiline_text(
        (x_header, header_y), 
        header_final, 
        font=font_main, 
        fill=(255, 255, 255),
        align="center"
    )
    
    # Рисуем основной текст (белый)
    bbox_main = draw.multiline_textbbox((0, 0), main_final, font=font_main, align="center")
    main_width = bbox_main[2] - bbox_main[0]
    x_main = (width - main_width) // 2
    
    # Обводка для основного текста
    for offset in [(-2,-2), (2,-2), (-2,2), (2,2)]:
        draw.multiline_text(
            (x_main + offset[0], main_y + offset[1]), 
            main_final, 
            font=font_main, 
            fill=(0, 0, 0),
            align="center"
        )
    
    draw.multiline_text(
        (x_main, main_y), 
        main_final, 
        font=font_main, 
        fill=(255, 255, 255),
        align="center"
    )
    
    return canvas

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Сохраняем сообщения до 20 слов
    if message.content and not message.content.startswith('v1!'):
        words = message.content.strip().split()
        word_count = len(words)
        
        if 1 <= word_count <= 20:
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
    """Создать демотиватор из двух случайных сообщений"""
    
    if len(message_history) < 2:
        await ctx.send("Нужно минимум 2 сообщения в базе. Пиши что-нибудь!")
        return
    
    async with ctx.typing():
        # Выбираем два РАЗНЫХ случайных сообщения
        msg1, msg2 = random.sample(list(message_history), 2)
        
        # Заголовок - текст первого сообщения
        header_text = msg1['text']
        # Основной текст - текст второго сообщения
        main_text = msg2['text']
        
        bg = await download_random_image()
        img = create_demotivator(header_text, main_text, bg)
        
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
        description="Берёт два случайных сообщения: верхнее и нижнее",
        color=0xff5500
    )
    embed.add_field(
        name="Команды",
        value=(
            "dem - случайный демотиватор (2 разных сообщения)\n"
            "dem_last - последние сообщения\n"
            "dem_stats - статистика\n"
            "dem_help - помощь"
        ),
        inline=False
    )
    embed.set_footer(text="Пиши в чат")
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Бот {bot.user} готов!")
    print(f"Сохраняю сообщения до 20 слов")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="чат | v1!dem"
        )
    )

if __name__ == "__main__":
    bot.run(TOKEN)
