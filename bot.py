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

# Flask app для поддержания жизн
app = Flask(__name__)

@app.route('/')
def home():
    return "Demotivator Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# Запускаем Flask в отдельном потоке
flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()

# Хранилище сообщений
message_history = deque(maxlen=500)

class DemotivatorBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        super().__init__(command_prefix='v1!', intents=intents)

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
    """Создаёт демотиватор с текстом нормального размера"""
    width, height = 1200, 1000
    img_width, img_height = 1000, 600
    
    canvas = Image.new('RGB', (width, height), color=(0, 0, 0))
    
    if background_img:
        bg_resized = background_img.resize((img_width, img_height))
        canvas.paste(bg_resized, ((width - img_width)//2, 80))
    
    draw = ImageDraw.Draw(canvas)
    
    # Рамка
    frame_x = (width - img_width)//2 - 5
    frame_y = 75
    draw.rectangle(
        [frame_x, frame_y, frame_x + img_width + 10, frame_y + img_height + 10],
        outline=(255, 255, 255),
        width=4
    )
    
    # **НОВЫЕ РАЗМЕРЫ: поменьше**
    words = text.split()
    word_count = len(words)
    
    if word_count <= 2:
        font_size = 90   # Было 140
    elif word_count <= 3:
        font_size = 80   # Было 120
    elif word_count <= 4:
        font_size = 70   # Было 100
    else:
        font_size = 60   # Было 80
    
    font_big = get_font(font_size, bold=True)
    font_small = get_font(24)  # Поменьше для автора
    
    # Разбиваем на строки
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        # По 2-3 слова в строке, но не больше
        if len(current_line) >= 3 or len(' '.join(current_line)) > 20:
            lines.append(' '.join(current_line))
            current_line = []
    
    if current_line:
        lines.append(' '.join(current_line))
    
    final_text = '\n'.join(lines)
    
    # Центрируем текст
    bbox = draw.multiline_textbbox((0, 0), final_text, font=font_big, align="center")
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (width - text_width) // 2
    # Текст выше, чтобы точно влезал
    y = height - 280  # Можно регулировать
    
    # Обводка
    for offset in [(-4,-4), (4,-4), (-4,4), (4,4)]:
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
    
    # Автор
    author_text = f"— {author_name}"
    bbox_author = draw.textbbox((0, 0), author_text, font=font_small)
    author_width = bbox_author[2] - bbox_author[0]
    x_author = (width - author_width) // 2
    y_author = y + 90  # Поднял ближе к тексту
    
    for offset in [(-1,-1), (1,-1), (-1,1), (1,1)]:
        draw.text((x_author + offset[0], y_author + offset[1]), author_text, font=font_small, fill=(0,0,0))
    draw.text((x_author, y_author), author_text, font=font_small, fill=(180,180,180))
    
    return canvas


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if message.content and not message.content.startswith('v1!'):
        words = message.content.strip().split()
        word_count = len(words)
        
        if 2 <= word_count <= 6:
            message_history.append({
                'text': message.content.upper(),
                'author': message.author.display_name,
                'time': datetime.datetime.now(),
                'words': word_count
            })
            print(f"📝 Добавлено ({word_count} слов): {message.content[:30]}...")
    
    await bot.process_commands(message)

@bot.command(name="dem")
async def dem_command(ctx):
    if len(message_history) == 0:
        await ctx.send("❌ В истории пока нет сообщений! Напиши что-нибудь (2-6 слов).")
        return
    
    async with ctx.typing():
        msg_data = random.choice(list(message_history))
        
        status = await ctx.send(f"🔄 Беру сообщение от {msg_data['author']}...")
        
        bg = await download_random_image()
        img = create_demotivator(msg_data['text'], msg_data['author'], bg)
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        await status.delete()
        
        file = discord.File(img_buffer, filename='demotivator.png')
        await ctx.send(f"**{msg_data['text']}**\n— {msg_data['author']}", file=file)

@bot.command(name="dem_last")
async def dem_last_command(ctx):
    if len(message_history) == 0:
        await ctx.send("❌ История пуста")
        return
    
    last_messages = list(message_history)[-10:]
    
    embed = discord.Embed(title="📜 Последние сообщения", color=0x3498db)
    for msg in reversed(last_messages):
        embed.add_field(
            name=f"{msg['author']} ({msg['words']} сл.)",
            value=msg['text'][:50],
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name="dem_stats")
async def dem_stats_command(ctx):
    embed = discord.Embed(title="📊 Статистика", color=0x00ff00)
    embed.add_field(name="Сообщений в базе", value=str(len(message_history)), inline=True)
    
    if message_history:
        word_dist = {}
        for msg in message_history:
            word_dist[msg['words']] = word_dist.get(msg['words'], 0) + 1
        
        dist_text = "\n".join([f"{w} слов: {c}" for w, c in sorted(word_dist.items())])
        embed.add_field(name="Распределение", value=dist_text, inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="dem_help")
async def dem_help_command(ctx):
    embed = discord.Embed(
        title="🎭 ДЕМОТИВАТОР БОТ",
        description="Превращает короткие сообщения (2-6 слов) в демотиваторы",
        color=0xff5500
    )
    embed.add_field(
        name="Команды",
        value=(
            "`v1!dem` - случайный демотиватор\n"
            "`v1!dem_last` - последние сообщения\n"
            "`v1!dem_stats` - статистика\n"
            "`v1!dem_help` - помощь"
        )
    )
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} готов!")
    print(f"📡 Поддерживает русский язык")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="чат | v1!dem")
    )

if __name__ == "__main__":
    bot.run(TOKEN)
