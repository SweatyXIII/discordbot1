import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter
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

@app.route('/healthz')
def health():
    return "OK", 200

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
            url = "https://picsum.photos/1200/1200"
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    img_data = await resp.read()
                    img = Image.open(io.BytesIO(img_data))
                    return img.resize((1200, 1200))
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
    if not words:
        return []
    
    lines = []
    current_line = [words[0]]
    
    for word in words[1:]:
        temp_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), temp_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def create_demotivator(header_text, main_text, background_img=None):
    """Создаёт обычный демотиватор: заголовок -> картинка -> основной текст"""
    width, height = 1200, 1000
    img_width, img_height = 1000, 600
    
    canvas = Image.new('RGB', (width, height), color=(0, 0, 0))
    
    # Определяем размер шрифта
    all_words = (header_text + " " + main_text).split()
    total_words = len(all_words)
    
    if total_words <= 4:
        font_size = 70
    elif total_words <= 8:
        font_size = 60
    elif total_words <= 12:
        font_size = 50
    elif total_words <= 20:
        font_size = 45
    elif total_words <= 30:
        font_size = 38
    else:
        font_size = 32
    
    font_main = get_font(font_size, bold=True)
    
    # Максимальная ширина текста
    max_text_width = width - 100
    
    # Временный draw для измерений
    temp_draw = ImageDraw.Draw(canvas)
    
    # Разбиваем тексты на строки
    header_lines = wrap_text(header_text, font_main, temp_draw, max_text_width)
    main_lines = wrap_text(main_text, font_main, temp_draw, max_text_width)
    
    header_final = '\n'.join(header_lines)
    main_final = '\n'.join(main_lines)
    
    # Высота текстов
    bbox_header = temp_draw.multiline_textbbox((0, 0), header_final, font=font_main)
    header_height = bbox_header[3] - bbox_header[1]
    
    bbox_main = temp_draw.multiline_textbbox((0, 0), main_final, font=font_main)
    main_height = bbox_main[3] - bbox_main[1]
    
    # Расчет позиций
    total_height = header_height + img_height + main_height
    start_y = (height - total_height) // 2
    
    header_y = start_y
    img_y = header_y + header_height + 30
    main_y = img_y + img_height + 30
    
    # Рисуем фон
    if background_img:
        bg_resized = background_img.resize((img_width, img_height))
        canvas.paste(bg_resized, ((width - img_width)//2, img_y))
    else:
        # Градиент
        for i in range(img_height):
            color = int(50 + (i / img_height) * 100)
            draw_temp = ImageDraw.Draw(canvas)
            draw_temp.rectangle(
                [(width - img_width)//2, img_y + i, (width + img_width)//2, img_y + i + 1],
                fill=(color, color, color)
            )
    
    draw = ImageDraw.Draw(canvas)
    
    # Рамка вокруг картинки
    frame_x = (width - img_width)//2 - 5
    frame_y = img_y - 5
    draw.rectangle(
        [frame_x, frame_y, frame_x + img_width + 10, frame_y + img_height + 10],
        outline=(255, 255, 255),
        width=4
    )
    
    # Рисуем заголовок
    bbox_header = draw.multiline_textbbox((0, 0), header_final, font=font_main, align="center")
    header_width = bbox_header[2] - bbox_header[0]
    x_header = (width - header_width) // 2
    
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
    
    # Рисуем основной текст
    bbox_main = draw.multiline_textbbox((0, 0), main_final, font=font_main, align="center")
    main_width = bbox_main[2] - bbox_main[0]
    x_main = (width - main_width) // 2
    
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

def create_personal_demotivator(header_text, main_text, avatar_img=None):
    """Создаёт персональный демотиватор с аватаркой на весь фон и текстом с обводкой"""
    width, height = 1200, 1200
    
    # Создаём холст
    if avatar_img:
        # Растягиваем аватарку на весь фон
        canvas = avatar_img.resize((width, height)).convert('RGB')
    else:
        # Градиент если нет аватарки
        canvas = Image.new('RGB', (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        for i in range(height):
            color = int(20 + (i / height) * 40)
            draw.line([(0, i), (width, i)], fill=(color, color, color))
    
    draw = ImageDraw.Draw(canvas)
    
    # Определяем размер шрифта
    all_words = (header_text + " " + main_text).split()
    if len(all_words) <= 4:
        font_size = 80
    elif len(all_words) <= 8:
        font_size = 70
    elif len(all_words) <= 12:
        font_size = 60
    else:
        font_size = 50
    
    font_main = get_font(font_size, bold=True)
    
    # Максимальная ширина текста
    max_text_width = width - 200
    
    # Разбиваем тексты
    header_lines = wrap_text(header_text, font_main, draw, max_text_width)
    main_lines = wrap_text(main_text, font_main, draw, max_text_width)
    
    header_final = '\n'.join(header_lines)
    main_final = '\n'.join(main_lines)
    
    # Позиции текста
    header_y = 150
    main_y = height - 300
    
    # Заголовок сверху с обводкой
    bbox_header = draw.multiline_textbbox((0, 0), header_final, font=font_main, align="center")
    header_width = bbox_header[2] - bbox_header[0]
    x_header = (width - header_width) // 2
    
    # Тонкая чёрная обводка (2px)
    for offset in [(-2,-2), (2,-2), (-2,2), (2,2), (0,-2), (0,2), (-2,0), (2,0)]:
        draw.multiline_text(
            (x_header + offset[0], header_y + offset[1]), 
            header_final, 
            font=font_main, 
            fill=(0, 0, 0),
            align="center"
        )
    
    # Белый текст
    draw.multiline_text(
        (x_header, header_y), 
        header_final, 
        font=font_main, 
        fill=(255, 255, 255),
        align="center"
    )
    
    # Основной текст снизу с обводкой
    bbox_main = draw.multiline_textbbox((0, 0), main_final, font=font_main, align="center")
    main_width = bbox_main[2] - bbox_main[0]
    x_main = (width - main_width) // 2
    
    # Тонкая чёрная обводка (2px)
    for offset in [(-2,-2), (2,-2), (-2,2), (2,2), (0,-2), (0,2), (-2,0), (2,0)]:
        draw.multiline_text(
            (x_main + offset[0], main_y + offset[1]), 
            main_final, 
            font=font_main, 
            fill=(0, 0, 0),
            align="center"
        )
    
    # Белый текст
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
    """Создать обычный демотиватор из двух случайных сообщений"""
    
    if len(message_history) < 2:
        await ctx.send("Нужно минимум 2 сообщения в базе. Пиши что-нибудь!")
        return
    
    async with ctx.typing():
        msg1, msg2 = random.sample(list(message_history), 2)
        
        bg = await download_random_image()
        img = create_demotivator(msg1['text'], msg2['text'], bg)
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        file = discord.File(img_buffer, filename='demotivator.png')
        await ctx.send(file=file)

@bot.command(name="me")
async def me_command(ctx):
    """Создать персональный демотиватор из своих сообщений"""
    
    user_messages = [msg for msg in message_history if msg['author'] == ctx.author.display_name]
    
    if len(user_messages) < 2:
        await ctx.send("Нужно минимум 2 твоих сообщения в базе. Напиши что-нибудь ещё!")
        return
    
    async with ctx.typing():
        msg1, msg2 = random.sample(user_messages, 2)
        
        avatar_img = None
        if ctx.author.avatar:
            avatar_url = ctx.author.avatar.url
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url) as resp:
                    if resp.status == 200:
                        avatar_data = await resp.read()
                        avatar_img = Image.open(io.BytesIO(avatar_data))
        
        img = create_personal_demotivator(
            msg1['text'], 
            msg2['text'], 
            avatar_img
        )
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        file = discord.File(img_buffer, filename='personal_demotivator.png')
        await ctx.send(file=file)

@bot.command(name="random")
async def random_command(ctx):
    """Создать демотиватор из сообщений случайного пользователя"""
    
    if len(message_history) < 2:
        await ctx.send("Нужно минимум 2 сообщения в базе. Пиши что-нибудь!")
        return
    
    async with ctx.typing():
        authors = list(set([msg['author'] for msg in message_history]))
        random_author = random.choice(authors)
        
        author_messages = [msg for msg in message_history if msg['author'] == random_author]
        
        while len(author_messages) < 2:
            random_author = random.choice(authors)
            author_messages = [msg for msg in message_history if msg['author'] == random_author]
        
        msg1, msg2 = random.sample(author_messages, 2)
        
        target_user = None
        for member in ctx.guild.members:
            if member.display_name == random_author or member.name == random_author:
                target_user = member
                break
        
        avatar_img = None
        if target_user and target_user.avatar:
            avatar_url = target_user.avatar.url
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url) as resp:
                    if resp.status == 200:
                        avatar_data = await resp.read()
                        avatar_img = Image.open(io.BytesIO(avatar_data))
        
        img = create_personal_demotivator(
            msg1['text'], 
            msg2['text'], 
            avatar_img
        )
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        file = discord.File(img_buffer, filename=f'random_{random_author}.png')
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
        description="Три режима: общий, личный и случайный",
        color=0xff5500
    )
    embed.add_field(
        name="Команды",
        value=(
            "dem - случайный демотиватор (2 любых сообщения + картинка)\n"
            "me - твой персональный демотиватор (твоя аватарка на фоне)\n"
            "random - демотиватор случайного пользователя\n"
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
    print(f"Доступны команды: dem, me, random, dem_last, dem_stats, dem_help")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="чат | v1!dem, v1!me, v1!random"
        )
    )

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        error = error.original
    
    if isinstance(error, discord.Forbidden):
        await ctx.send("❌ У бота нет прав отправлять файлы в этот канал. Нужно включить `Attach Files`.")
    else:
        raise error

if __name__ == "__main__":
    bot.run(TOKEN)
