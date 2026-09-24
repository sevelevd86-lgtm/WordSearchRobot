import asyncio
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import aiohttp
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from dotenv import load_dotenv


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

USER_ID = int(
    os.getenv(
        "USER_ID",
        "5018476227"
    )
)

CITY = os.getenv(
    "CITY",
    "Москва"
)

TIMEZONE = ZoneInfo(
    os.getenv(
        "TIMEZONE",
        "Europe/Moscow"
    )
)

WAKE_TIME = os.getenv(
    "WAKE_TIME",
    "07:30"
)

SLEEP_TIME = os.getenv(
    "SLEEP_TIME",
    "22:30"
)

WEATHER_LAT = float(
    os.getenv(
        "WEATHER_LAT",
        "55.7558"
    )
)

WEATHER_LON = float(
    os.getenv(
        "WEATHER_LON",
        "37.6173"
    )
)

HOME_ADDRESS = os.getenv(
    "HOME_ADDRESS",
    ""
)

SCHOOL_ADDRESS = os.getenv(
    "SCHOOL_ADDRESS",
    ""
)

YANDEX_API_KEY = os.getenv(
    "YANDEX_API_KEY",
    ""
)

DB_FILE = "assistant.db"


if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не найден. "
        "Добавь его в Secrets/Environment Variables."
    )


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    )
)

logger = logging.getLogger(
    "personal_assistant"
)


# ============================================================
# BOT
# ============================================================

bot = Bot(
    token=BOT_TOKEN
)

dp = Dispatcher()

scheduler = AsyncIOScheduler(
    timezone=TIMEZONE
)


# ============================================================
# DAYS
# ============================================================

DAY_NAMES = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье"
]


DAY_NAMES_SHORT = [
    "Пн",
    "Вт",
    "Ср",
    "Чт",
    "Пт",
    "Сб",
    "Вс"
]


# ============================================================
# SCHOOL SCHEDULE
# ============================================================

SCHEDULE = {

    # --------------------------------------------------------
    # ПОНЕДЕЛЬНИК
    # --------------------------------------------------------

    0: [
        (
            "Классный час",
            "304"
        ),
        (
            "Английский язык",
            "404, 412"
        ),
        (
            "История",
            "402"
        ),
        (
            "Алгебра",
            "309"
        ),
        (
            "Обществознание",
            "402"
        ),
        (
            "Английский язык, практика",
            "404, 412"
        ),
        (
            "Информатика",
            "106, 107"
        ),
    ],


    # --------------------------------------------------------
    # ВТОРНИК
    # --------------------------------------------------------

    1: [
        (
            "Физика",
            "110"
        ),
        (
            "Геометрия",
            "309"
        ),
        (
            "Геометрия",
            "309"
        ),
        (
            "Английский язык",
            "404, 412"
        ),
        (
            "Литература",
            "Н-38, 413"
        ),
        (
            "Литература",
            "Н-38, 413"
        ),
        (
            "Физкультура",
            "Н-38"
        ),
        (
            "Физкультура",
            "Н-38"
        ),
    ],


    # --------------------------------------------------------
    # СРЕДА
    # --------------------------------------------------------

    2: [
        (
            "Алгебра",
            "309"
        ),
        (
            "Английский язык",
            "404, 412"
        ),
        (
            "История",
            "402"
        ),
        (
            "Вероятность",
            "309"
        ),
        (
            "Обществознание",
            "402"
        ),
        (
            "Химия",
            "409"
        ),
        (
            "История",
            "402"
        ),
    ],


    # --------------------------------------------------------
    # ЧЕТВЕРГ
    # --------------------------------------------------------

    3: [
        (
            "---",
            ""
        ),
        (
            "История",
            "402"
        ),
        (
            "Алгебра",
            "309"
        ),
        (
            "Алгебра",
            "309"
        ),
        (
            "Обществознание",
            "402"
        ),
        (
            "Проектная деятельность",
            "302"
        ),
        (
            "Русский язык",
            "409"
        ),
        (
            "География",
            "205"
        ),
    ],


    # --------------------------------------------------------
    # ПЯТНИЦА
    # --------------------------------------------------------

    4: [
        (
            "Русский язык",
            ""
        ),
        (
            "Литература",
            ""
        ),
        (
            "Биология",
            "407"
        ),
        (
            "Геометрия",
            "309"
        ),
        (
            "ОБЗР",
            ""
        ),
        (
            "Обществознание",
            "402"
        ),
        (
            "Основы права",
            "вн"
        ),
    ],
}


# ============================================================
# BELL SCHEDULE
# ============================================================

# Ты прислал:
#
# 1: 09:00 - 09:45
# 2: 10:00 - 10:45
# 3: 11:00 - 11:45
# 4: 11:55 - 12:40
# 5: 13:00 - 13:45
# 6: 14:05 - 14:50
# 7: 15:00 - 15:45
# 8: 15:55 - 16:40
#
# 8-й урок пока считаем именно таким.

LESSON_TIMES = [
    (
        "09:00",
        "09:45"
    ),
    (
        "10:00",
        "10:45"
    ),
    (
        "11:00",
        "11:45"
    ),
    (
        "11:55",
        "12:40"
    ),
    (
        "13:00",
        "13:45"
    ),
    (
        "14:05",
        "14:50"
    ),
    (
        "15:00",
        "15:45"
    ),
    (
        "15:55",
        "16:40"
    ),
]


# ============================================================
# MORNING SETTINGS
# ============================================================

WAKE_UP = "07:30"

PREPARATION_MINUTES = 35

METRO_TIME_MINUTES = 30

CAR_TIME_MINUTES = 20

SAFETY_BUFFER_MINUTES = 10

SCHOOL_START = "09:00"


# ============================================================
# WEATHER
# ============================================================

WEATHER_CODES = {

    0: "☀️ Ясно",

    1: "🌤 Преимущественно ясно",

    2: "⛅ Переменная облачность",

    3: "☁️ Пасмурно",

    45: "🌫 Туман",

    48: "🌫 Туман",

    51: "🌦 Лёгкая морось",

    53: "🌦 Морось",

    55: "🌧 Сильная морось",

    61: "🌧 Небольшой дождь",

    63: "🌧 Дождь",

    65: "🌧 Сильный дождь",

    71: "🌨 Снег",

    73: "🌨 Снег",

    75: "❄️ Сильный снег",

    80: "🌦 Ливень",

    81: "🌧 Ливень",

    82: "🌧 Сильный ливень",

    95: "⛈ Гроза",

    96: "⛈ Гроза с градом",

    99: "⛈ Сильная гроза",
}


# ============================================================
# DATABASE
# ============================================================

async def init_db():

    async with aiosqlite.connect(
        DB_FILE
    ) as db:

        # ----------------------------------------------------
        # TASKS
        # ----------------------------------------------------

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                deadline TEXT,
                completed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )

        # ----------------------------------------------------
        # EXPENSES
        # ----------------------------------------------------

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT,
                description TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        # ----------------------------------------------------
        # SAVINGS
        # ----------------------------------------------------

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS savings (
                user_id INTEGER PRIMARY KEY,
                target REAL DEFAULT 0,
                current REAL DEFAULT 0
            )
            """
        )

        # ----------------------------------------------------
        # ENGLISH
        # ----------------------------------------------------

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS english_progress (
                user_id INTEGER PRIMARY KEY,
                level TEXT DEFAULT 'A2',
                lessons_completed INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                total_answers INTEGER DEFAULT 0
            )
            """
        )

        # ----------------------------------------------------
        # SETTINGS
        # ----------------------------------------------------

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                user_id INTEGER PRIMARY KEY,
                monthly_income REAL DEFAULT 0,
                monthly_saving REAL DEFAULT 0,
                curfew TEXT DEFAULT '22:00'
            )
            """
        )

        # ----------------------------------------------------
        # USER INIT
        # ----------------------------------------------------

        await db.execute(
            """
            INSERT OR IGNORE INTO settings
            (user_id, monthly_income, monthly_saving, curfew)
            VALUES (?, 0, 0, '22:00')
            """,
            (
                USER_ID,
            )
        )

        await db.execute(
            """
            INSERT OR IGNORE INTO english_progress
            (user_id, level)
            VALUES (?, 'A2')
            """,
            (
                USER_ID,
            )
        )

        await db.execute(
            """
            INSERT OR IGNORE INTO savings
            (user_id, target, current)
            VALUES (?, 0, 0)
            """,
            (
                USER_ID,
            )
        )

        await db.commit()


# ============================================================
# SECURITY
# ============================================================

def is_allowed(
    user_id: int
) -> bool:

    return user_id == USER_ID


async def deny(
    message: Message
):

    await message.answer(
        "⛔ Этот бот является личным."
    )


# ============================================================
# KEYBOARD
# ============================================================

def main_keyboard():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="🧠 Мой день",
        callback_data="my_day"
    )

    builder.button(
        text="📅 Расписание",
        callback_data="schedule"
    )

    builder.button(
        text="📝 Задачи",
        callback_data="tasks"
    )

    builder.button(
        text="🇬🇧 Английский",
        callback_data="english"
    )

    builder.button(
        text="💰 Финансы",
        callback_data="finance"
    )

    builder.button(
        text="🌦 Погода",
        callback_data="weather"
    )

    builder.button(
        text="🚇 Дорога",
        callback_data="route"
    )

    builder.button(
        text="⚙️ Настройки",
        callback_data="settings"
    )

    builder.adjust(
        2,
        2,
        2,
        2
    )

    return builder.as_markup()


# ============================================================
# TIME HELPERS
# ============================================================

def time_to_minutes(
    value: str
) -> int:

    hours, minutes = map(
        int,
        value.split(":")
    )

    return hours * 60 + minutes


def minutes_to_time(
    total: int
) -> str:

    total %= 24 * 60

    hours = total // 60

    minutes = total % 60

    return (
        f"{hours:02d}:"
        f"{minutes:02d}"
    )


def calculate_morning_times():

    school_start = time_to_minutes(
        SCHOOL_START
    )

    metro_departure = (
        school_start
        - METRO_TIME_MINUTES
        - SAFETY_BUFFER_MINUTES
    )

    car_departure = (
        school_start
        - CAR_TIME_MINUTES
        - SAFETY_BUFFER_MINUTES
    )

    return {
        "metro": minutes_to_time(
            metro_departure
        ),
        "car": minutes_to_time(
            car_departure
        ),
    }


# ============================================================
# WEATHER REQUEST
# ============================================================

async def get_weather():

    url = (
        "https://api.open-meteo.com/"
        "v1/forecast"
    )

    params = {

        "latitude": WEATHER_LAT,

        "longitude": WEATHER_LON,

        "current": (
            "temperature_2m,"
            "apparent_temperature,"
            "precipitation,"
            "weather_code,"
            "wind_speed_10m"
        ),

        "hourly": (
            "temperature_2m,"
            "precipitation_probability,"
            "weather_code"
        ),

        "timezone": "Europe/Moscow",

        "forecast_days": 1,
    }

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(
                url,
                params=params,
                timeout=10
            ) as response:

                if response.status != 200:

                    logger.error(
                        "Weather HTTP %s",
                        response.status
                    )

                    return None

                return await response.json()

    except Exception as error:

        logger.error(
            "Weather error: %s",
            error
        )

        return None


# ============================================================
# WEATHER TEXT
# ============================================================

async def weather_text():

    data = await get_weather()

    if not data:

        return (
            "🌦 **Погода**\n\n"
            "Временно недоступна."
        )

    current = data.get(
        "current",
        {}
    )

    temperature = current.get(
        "temperature_2m",
        "?"
    )

    feels = current.get(
        "apparent_temperature",
        "?"
    )

    wind = current.get(
        "wind_speed_10m",
        "?"
    )

    code = current.get(
        "weather_code"
    )

    description = WEATHER_CODES.get(
        code,
        "🌤 Неизвестно"
    )

    return f"""
🌦 **ПОГОДА — {CITY}**

{description}

🌡 Температура: **{temperature}°C**

🤚 Ощущается: **{feels}°C**

💨 Ветер: **{wind} км/ч**
"""


# ============================================================
# SCHEDULE TEXT
# ============================================================

def get_day_schedule(
    day_index: int
):

    return SCHEDULE.get(
        day_index,
        []
    )


def schedule_text(
    day_index: int
):

    lessons = get_day_schedule(
        day_index
    )

    if not lessons:

        return (
            f"📅 **{DAY_NAMES[day_index]}**\n\n"
            "😴 Занятий нет.\n"
        )

    text = (
        f"📅 **{DAY_NAMES[day_index]}**\n\n"
    )

    for index, (
        subject,
        room
    ) in enumerate(
        lessons,
        start=1
    ):

        if index <= len(
            LESSON_TIMES
        ):

            start, end = LESSON_TIMES[
                index - 1
            ]

        else:

            start = "--:--"
            end = "--:--"

        if subject == "---":

            text += (
                f"{index}. "
                f"⏰ {start}–{end}\n"
                f"   ⬜ Свободное окно\n\n"
            )

            continue

        text += (
            f"{index}. "
            f"⏰ **{start}–{end}**\n"
            f"   📚 **{subject}**"
        )

        if room:

            text += (
                f"\n   🚪 Кабинет: **{room}**"
            )

        text += "\n\n"

    return text


# ============================================================
# TODAY SCHEDULE
# ============================================================

def today_schedule_text():

    now = datetime.now(
        TIMEZONE
    )

    day_index = now.weekday()

    return schedule_text(
        day_index
    )


# ============================================================
# TOMORROW SCHEDULE
# ============================================================

def tomorrow_schedule_text():

    now = datetime.now(
        TIMEZONE
    )

    tomorrow = (
        now + timedelta(
            days=1
        )
    )

    return schedule_text(
        tomorrow.weekday()
    )


# ============================================================
# MY DAY
# ============================================================

async def build_my_day():

    now = datetime.now(
        TIMEZONE
    )

    day_index = now.weekday()

    date_string = now.strftime(
        "%d.%m.%Y"
    )

    morning = calculate_morning_times()

    lessons = get_day_schedule(
        day_index
    )

    weather = await weather_text()

    text = f"""
☀️ **МОЙ ДЕНЬ**

📆 {date_string}
📍 {DAY_NAMES[day_index]}

━━━━━━━━━━━━━━━━━━

⏰ **УТРО**

🛌 Подъём:
**07:30**

🚿 Умыться / собраться:
**07:30–08:05**

━━━━━━━━━━━━━━━━━━

🚇 **ЕСЛИ МЕТРО**

🚪 Выйти:
**{morning["metro"]}**

🚇 Дорога:
~30 минут

⏱ Запас:
10 минут

🏫 В школе:
примерно **08:50**

━━━━━━━━━━━━━━━━━━

🚗 **ЕСЛИ МАШИНА**

🚪 Выехать:
**{morning["car"]}**

🚗 Дорога:
~15–20 минут

🏫 В школе:
примерно **08:50**

━━━━━━━━━━━━━━━━━━

{weather}

━━━━━━━━━━━━━━━━━━

🎓 **ШКОЛА**

"""

    if lessons:

        for index, (
            subject,
            room
        ) in enumerate(
            lessons,
            start=1
        ):

            start, end = LESSON_TIMES[
                index - 1
            ]

            if subject == "---":

                text += (
                    f"⬜ {index}. "
                    f"{start}–{end} — "
                    f"свободное окно\n"
                )

            else:

                text += (
                    f"{index}. "
                    f"**{start}–{end}** — "
                    f"{subject}"
                )

                if room:

                    text += (
                        f" · {room}"
                    )

                text += "\n"

    else:

        text += (
            "😴 Сегодня школы нет.\n"
        )

    # --------------------------------------------------------
    # SCHOOL END
    # --------------------------------------------------------

    if lessons:

        last_lesson = min(
            len(lessons),
            len(LESSON_TIMES)
        )

        school_end = LESSON_TIMES[
            last_lesson - 1
        ][1]

        text += (
            f"\n🏁 Конец школы: "
            f"**{school_end}**\n"
        )

    text += """

━━━━━━━━━━━━━━━━━━

🇬🇧 **АНГЛИЙСКИЙ**

Сегодня:
**30 минут**

📚 10 минут — грамматика
🧠 10 минут — упражнения
📝 5 минут — слова
🔁 5 минут — повторение

━━━━━━━━━━━━━━━━━━

😴 **СОН**

Лечь:
**22:30**

Подъём:
**07:30**

Сон:
**9 часов**

━━━━━━━━━━━━━━━━━━

💰 **ФИНАНСЫ**

Не забудь записывать расходы:

`/spend 350 еда`

━━━━━━━━━━━━━━━━━━

🏠 **ВОЗВРАЩЕНИЕ**

Крайнее время возвращения
настраивается в разделе
⚙️ Настройки.

"""

    return text


# ============================================================
# START
# ============================================================

@dp.message(
    CommandStart()
)
async def start_handler(
    message: Message
):

    if not is_allowed(
        message.from_user.id
    ):

        await deny(
            message
        )

        return

    await message.answer(
        """
🐻 **ТВОЙ ЛИЧНЫЙ АССИСТЕНТ**

Привет!

Я буду помогать тебе
организовывать каждый день.

📅 Расписание
⏰ Подъём и сон
🚇 Дорога
🌦 Погода
💰 Финансы
🇬🇧 Английский
📝 Задачи
🏠 Возвращение домой

Каждое утро я могу присылать
тебе готовый план дня.

Нажми:

🧠 **Мой день**
""",
        reply_markup=main_keyboard()
    )


# ============================================================
# /TODAY
# ============================================================

@dp.message(
    Command("today")
)
async def today_command(
    message: Message
):

    if not is_allowed(
        message.from_user.id
    ):

        await deny(
            message
        )

        return

    await message.answer(
        await build_my_day(),
        reply_markup=main_keyboard()
    )


# ============================================================
# /TOMORROW
# ============================================================

@dp.message(
    Command("tomorrow")
)
async def tomorrow_command(
    message: Message
):

    if not is_allowed(
        message.from_user.id
    ):

        await deny(
            message
        )

        return

    await message.answer(
        tomorrow_schedule_text(),
        reply_markup=main_keyboard()
    )


# ============================================================
# MY DAY CALLBACK
# ============================================================

@dp.callback_query(
    F.data == "my_day"
)
async def my_day_callback(
    callback: CallbackQuery
):

    if not is_allowed(
        callback.from_user.id
    ):

        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True
        )

        return

    await callback.message.edit_text(
        await build_my_day(),
        reply_markup=main_keyboard()
    )

    await callback.answer()


# ============================================================
# SCHEDULE CALLBACK
# ============================================================

@dp.callback_query(
    F.data == "schedule"
)
async def schedule_callback(
    callback: CallbackQuery
):

    if not is_allowed(
        callback.from_user.id
    ):

        return

    text = (
        "📅 **РАСПИСАНИЕ НА НЕДЕЛЮ**\n\n"
    )

    for day in range(5):

        text += schedule_text(
            day
        )

        text += (
            "\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=main_keyboard()
    )

    await callback.answer()


# ============================================================
# WEATHER CALLBACK
# ============================================================

@dp.callback_query(
    F.data == "weather"
)
async def weather_callback(
    callback: CallbackQuery
):

    if not is_allowed(
        callback.from_user.id
    ):

        return

    await callback.message.edit_text(
        await weather_text(),
        reply_markup=main_keyboard()
    )

    await callback.answer()


# ============================================================
# ROUTE CALLBACK
# ============================================================

@dp.callback_query(
    F.data == "route"
)
async def route_callback(
    callback: CallbackQuery
):

    if not is_allowed(
        callback.from_user.id
    ):

        return

    morning = calculate_morning_times()

    text = f"""
🚇 **ДОРОГА ДО ШКОЛЫ**

Сейчас используются твои
примерные значения.

━━━━━━━━━━━━━━━━━━

🚇 **МЕТРО**

Дорога:
~30 минут

Выйти:
**{morning["metro"]}**

Прибытие:
~08:50

━━━━━━━━━━━━━━━━━━

🚗 **МАШИНА**

Дорога:
~15–20 минут

Выехать:
**{morning["car"]}**

Прибытие:
~08:50

━━━━━━━━━━━━━━━━━━

🏫 Первый урок:
**09:00**

⏱ Запас:
**10 минут**

━━━━━━━━━━━━━━━━━━

Позже подключим настоящий
расчёт маршрута, чтобы бот
сам смотрел ситуацию на дороге
и говорил, когда тебе выходить.
"""

    await callback.message.edit_text(
        text,
        reply_markup=main_keyboard()
    )

    await callback.answer()


# ============================================================
# ENGLISH CALLBACK
# ============================================================

@dp.callback_query(
    F.data == "english"
)
async def english_callback(
    callback: CallbackQuery
):

    if not is_allowed(
        callback.from_user.id
    ):

        return

    async with aiosqlite.connect(
        DB_FILE
    ) as db:

        cursor = await db.execute(
            """
            SELECT
                level,
                lessons_completed,
                correct_answers,
                total_answers
            FROM english_progress
            WHERE user_id = ?
            """,
            (
                USER_ID,
            )
        )

        row = await cursor.fetchone()

    if row:

        level = row[0]
        completed = row[1]
        correct = row[2]
        total = row[3]

    else:

        level = "A2"
        completed = 0
        correct = 0
        total = 0

    if total > 0:

        accuracy = (
            correct / total
        ) * 100

    else:

        accuracy = 0

    text = f"""
🇬🇧 **АНГЛИЙСКИЙ**

Текущий уровень:
**{level}**

📚 Завершено занятий:
**{completed}**

🎯 Правильных ответов:
**{correct}/{total}**

📊 Точность:
**{accuracy:.0f}%**

━━━━━━━━━━━━━━━━━━

⏱ Сегодня:
**30 минут**

📖 План:

1️⃣ 5 минут — слова

2️⃣ 10 минут — грамматика

3️⃣ 10 минут — упражнения

4️⃣ 5 минут — повторение

━━━━━━━━━━━━━━━━━━

🎯 Текущий этап:

**A2 → B1**

Будем постепенно проходить:

• Present Simple
• Present Continuous
• Past Simple
• Future
• Present Perfect
• модальные глаголы
• условные предложения
• артикли
• предлоги
• словарный запас
• чтение
• аудирование
"""

    await callback.message.edit_text(
        text,
        reply_markup=main_keyboard()
    )

    await callback.answer()


# ============================================================
# TASKS CALLBACK
# ============================================================

@dp.callback_query(
    F.data == "tasks"
)
async def tasks_callback(
    callback: CallbackQuery
):

    if not is_allowed(
        callback.from_user.id
    ):

        return

    async with aiosqlite.connect(
        DB_FILE
    ) as db:

        cursor = await db.execute(
            """
            SELECT
                id,
                text,
                deadline
            FROM tasks
            WHERE user_id = ?
            AND completed = 0
            ORDER BY id DESC
            """,
            (
                USER_ID,
            )
        )

        rows = await cursor.fetchall()

    text = "📝 **МОИ ЗАДАЧИ**\n\n"

    if not rows:

        text += (
            "У тебя пока нет задач.\n\n"
        )

    else:

        for (
            task_id,
            task,
            deadline
        ) in rows:

            text += (
                f"▫️ {task}"
            )

            if deadline:

                text += (
                    f" — {deadline}"
                )

            text += "\n"

    text += """
━━━━━━━━━━━━━━━━━━

Добавить задачу:

`/task Сделать домашнюю работу`

Удалить/завершить задачи
добавим следующим этапом.
"""

    await callback.message.edit_text(
        text,
        reply_markup=main_keyboard()
    )

    await callback.answer()


# ============================================================
# ADD TASK
# ============================================================

@dp.message(
    Command("task")
)
async def add_task(
    message: Message
):

    if not is_allowed(
        message.from_user.id
    ):

        await deny(
            message
        )

        return

    text = message.text.replace(
        "/task",
        "",
        1
    ).strip()

    if not text:

        await message.answer(
            """
Пример:

`/task Сделать домашнюю работу`
"""
        )

        return

    created_at = datetime.now(
        TIMEZONE
    ).isoformat()

    async with aiosqlite.connect(
        DB_FILE
    ) as db:

        await db.execute(
            """
            INSERT INTO tasks
            (
                user_id,
                text,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                USER_ID,
                text,
                created_at
            )
        )

        await db.commit()

    await message.answer(
        f"""
✅ **Задача добавлена**

{text}
""",
        reply_markup=main_keyboard()
    )


# ============================================================
# FINANCE CALLBACK
# ============================================================

@dp.callback_query(
    F.data == "finance"
)
async def finance_callback(
    callback: CallbackQuery
):

    if not is_allowed(
        callback.from_user.id
    ):

        return

    async with aiosqlite.connect(
        DB_FILE
    ) as db:

        # income
        cursor = await db.execute(
            """
            SELECT
                monthly_income,
                monthly_saving,
                curfew
            FROM settings
            WHERE user_id = ?
            """,
            (
                USER_ID,
            )
        )

        settings = await cursor.fetchone()

        # total spent
        cursor = await db.execute(
            """
            SELECT
                COALESCE(SUM(amount), 0)
            FROM expenses
            WHERE user_id = ?
            """,
            (
                USER_ID,
            )
        )

        spent_result = await cursor.fetchone()

        # savings
        cursor = await db.execute(
            """
            SELECT
                target,
                current
            FROM savings
            WHERE user_id = ?
            """,
            (
                USER_ID,
            )
        )

        savings = await cursor.fetchone()

    if settings:

        income = settings[0] or 0
        monthly_saving = settings[1] or 0
        curfew = settings[2] or "22:00"

    else:

        income = 0
        monthly_saving = 0
        curfew = "22:00"

    spent = (
        spent_result[0]
        if spent_result
        else 0
    )

    target = (
        savings[0]
        if savings
        else 0
    )

    current = (
        savings[1]
        if savings
        else 0
    )

    available = (
        income
        - monthly_saving
        - spent
    )

    text = f"""
💰 **ФИНАНСЫ**

💵 Доход:
**{income:.0f} ₽**

🎯 План накоплений:
**{monthly_saving:.0f} ₽**

💸 Потрачено:
**{spent:.0f} ₽**

💳 Осталось свободных денег:
**{available:.0f} ₽**

━━━━━━━━━━━━━━━━━━

🎯 **НАКОПЛЕНИЯ**

Накоплено:
**{current:.0f} ₽**

Цель:
**{target:.0f} ₽**

━━━━━━━━━━━━━━━━━━

🏠 Возвращение домой:
**{curfew}**

━━━━━━━━━━━━━━━━━━

Команды:

`/income 50000`

`/save 20000`

`/spend 350 еда`

`/goal 100000`

`/saved 35000`
"""

    await callback.message.edit_text(
        text,
        reply_markup=main_keyboard()
    )

    await callback.answer()


# ============================================================
# SET INCOME
# ============================================================

@dp.message(
    Command("income")
)
async def income_command(
    message: Message
):

    if not is_allowed(
        message.from_user.id
    ):

        await deny(
            message
        )

        return

    parts = message.text.split()

    if len(parts) < 2:

        await message.answer(
            "Пример:\n\n"
            "`/income 50000`"
        )

        return

    try:

        amount = float(
            parts[1]
        )

    except ValueError:

        await message.answer(
            "Сумма должна быть числом."
        )

        return

    async with aiosqlite.connect(
        DB_FILE
    ) as db:

        await db.execute(
            """
            INSERT INTO settings
            (
                user_id,
                monthly_income
            )
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
            monthly_income =
            excluded.monthly_income
            """,
            (
                USER_ID,
                amount
            )
        )

        await db.commit()

    await message.answer(
        f"""
💰 Доход установлен:

**{amount:.0f} ₽ / месяц**
"""
    )


# ============================================================
# SET SAVING
# ============================================================

@dp.message(
    Command("save")
)
async def save_command(
    message: Message
):

    if not is_allowed(
        message.from_user.id
    ):

        await deny(
            message
        )

        return

    parts = message.text.split()

    if len(parts) < 2:

        await message.answer(
            "Пример:\n\n"
            "`/save 20000`"
        )

        return

    try:

        amount = float(
            parts[1]
        )

    except ValueError:

        await message.answer(
            "Сумма должна быть числом."
        )

        return

    async with aiosqlite.connect(
        DB_FILE
    ) as db:

        await db.execute(
            """
            INSERT INTO settings
            (
                user_id,
                monthly_saving
            )
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
            monthly_saving =
            excluded.monthly_saving
            """,
            (
                USER_ID,
                amount
            )
        )

        await db.commit()

    await message.answer(
        f"""
🎯 План накоплений установлен:

**{amount:.0f} ₽ / месяц**
"""
    )


# ============================================================
# SPEND
# ============================================================

@dp.message(
    Command("spend")
)
async def spend_command(
    message: Message
):

    if not is_allowed(
        message.from_user.id
    ):

        await deny(
            message
        )

        return

    parts = message.text.split(
        maxsplit=2
    )

    if len(parts) < 2:

        await message.answer(
            """
Пример:

`/spend 350 еда`
"""
        )

        return

    try:

        amount = float(
            parts[1]
        )

    except ValueError:

        await message.answer(
            "Сумма должна быть числом."
        )

        return

    category = (
        parts[2]
        if len(parts) >= 3
        else "Другое"
    )

    created_at = datetime.now(
        TIMEZONE
    ).isoformat()

    async with aiosqlite.connect(
        DB_FILE
    ) as db:

        await db.execute(
            """
            INSERT INTO expenses
            (
                user_id,
                amount,
                category,
                description,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                USER_ID,
                amount,
                category,
                category,
                created_at
            )
        )

        await db.commit()

    await message.answer(
        f"""
💸 **Расход записан**

Сумма:
**{amount:.0f} ₽**

Категория:
**{category}**
"""
    )


# ============================================================
# SAVINGS GOAL
# ============================================================

@dp.message(
    Command("goal")
)
async def goal_command(
    message: Message
):

    if not is_allowed(
        message.from_user.id
    ):

        await deny(
            message
        )

        return

    parts = message.text.split()

    if len(parts) < 2:

        await message.answer(
            "Пример:\n\n"
            "`/goal 100000`"
        )

        return

    try:

        target = float(
            parts[1]
        )

    except ValueError:

        await message.answer(
            "Сумма должна быть числом."
        )

        return

    async with aiosqlite.connect(
        DB_FILE
    ) as db:

        await db.execute(
            """
            INSERT INTO savings
            (
                user_id,
                target
            )
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
            target = excluded.target
            """,
            (
                USER_ID,
                target
            )
        )

        await db.commit()

    await message.answer(
        f"""
🎯 Цель установлена:

**{target:.0f} ₽**
"""
    )


# ============================================================
# SAVED MONEY
# ============================================================

@dp.message(
    Command("saved")
)
async def saved_command(
    message: Message
):

    if not is_allowed(
        message.from_user.id
    ):

        await deny(
            message
        )

        return

    parts = message.text.split()

    if len(parts) < 2:

        await message.answer(
            "Пример:\n\n"
            "`/saved 35000`"
        )

        return

    try:

        current = float(
            parts[1]
        )

    except ValueError:

        await message.answer(
            "Сумма должна быть числом."
        )

        return

    async with aiosqlite.connect(
        DB_FILE
    ) as db:

        await db.execute(
            """
            INSERT INTO savings
            (
                user_id,
                current
            )
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
            current = excluded.current
            """,
            (
                USER_ID,
                current
            )
        )

        await db.commit()

    await message.answer(
        f"""
💰 Текущие накопления:

**{current:.0f} ₽**
"""
    )


# ============================================================
# SETTINGS CALLBACK
# ============================================================

@dp.callback_query(
    F.data == "settings"
)
async def settings_callback(
    callback: CallbackQuery
):

    if not is_allowed(
        callback.from_user.id
    ):

        return

    morning = calculate_morning_times()

    async with aiosqlite.connect(
        DB_FILE
    ) as db:

        cursor = await db.execute(
            """
            SELECT curfew
            FROM settings
            WHERE user_id = ?
            """,
            (
                USER_ID,
            )
        )

        row = await cursor.fetchone()

    curfew = (
        row[0]
        if row
        else "22:00"
    )

    text = f"""
⚙️ **НАСТРОЙКИ**

━━━━━━━━━━━━━━━━━━

⏰ Подъём:
**07:30**

😴 Сон:
**22:30**

🛌 Сон:
**9 часов**

━━━━━━━━━━━━━━━━━━

🏫 Школа:

Начало:
**09:00**

━━━━━━━━━━━━━━━━━━

🚇 Метро:

~30 минут

Выход:
**{morning["metro"]}**

━━━━━━━━━━━━━━━━━━

🚗 Машина:

~15–20 минут

Выезд:
**{morning["car"]}**

━━━━━━━━━━━━━━━━━━

🏠 Вернуться домой:

**{curfew}**

━━━━━━━━━━━━━━━━━━

📍 Город:

**{CITY}**

🕐 Часовой пояс:

**Europe/Moscow**
"""

    await callback.message.edit_text(
        text,
        reply_markup=main_keyboard()
    )

    await callback.answer()


# ============================================================
# MORNING PLAN
# ============================================================

async def send_morning_plan():

    try:

        await bot.send_message(
            USER_ID,
            await build_my_day(),
            reply_markup=main_keyboard()
        )

        logger.info(
            "Morning plan sent"
        )

    except Exception as error:

        logger.error(
            "Morning plan error: %s",
            error
        )


# ============================================================
# NIGHT PLAN
# ============================================================

async def send_night_plan():

    try:

        tomorrow = (
            datetime.now(
                TIMEZONE
            )
            + timedelta(
                days=1
            )
        )

        day_index = tomorrow.weekday()

        text = f"""
🌙 **ПЛАН НА ЗАВТРА**

📆 {tomorrow.strftime("%d.%m.%Y")}

📅 {DAY_NAMES[day_index]}

━━━━━━━━━━━━━━━━━━

{schedule_text(day_index)}

━━━━━━━━━━━━━━━━━━

⏰ Подъём:

**07:30**

😴 Лечь:

**22:30**

💤 Сон:

**9 часов**

━━━━━━━━━━━━━━━━━━

🚇 Если метро:

Выйти около
**{calculate_morning_times()["metro"]}**

🚗 Если машина:

Выехать около
**{calculate_morning_times()["car"]}**

━━━━━━━━━━━━━━━━━━

Доброй ночи 🐻
"""

        await bot.send_message(
            USER_ID,
            text,
            reply_markup=main_keyboard()
        )

    except Exception as error:

        logger.error(
            "Night plan error: %s",
            error
        )


# ============================================================
# ENGLISH REMINDER
# ============================================================

async def send_english_reminder():

    try:

        await bot.send_message(
            USER_ID,
            """
🇬🇧 **ВРЕМЯ АНГЛИЙСКОГО**

Сегодня твои 30 минут.

━━━━━━━━━━━━━━━━━━

📖 10 минут
Грамматика

🧠 10 минут
Упражнения

📝 5 минут
Слова

🔁 5 минут
Повторение

━━━━━━━━━━━━━━━━━━

Начинаем?
""",
            reply_markup=main_keyboard()
        )

    except Exception as error:

        logger.error(
            "English reminder error: %s",
            error
        )


# ============================================================
# SCHOOL REMINDER
# ============================================================

async def send_leave_reminder():

    try:

        now = datetime.now(
            TIMEZONE
        )

        day_index = now.weekday()

        if day_index >= 5:

            return

        lessons = get_day_schedule(
            day_index
        )

        if not lessons:

            return

        morning = calculate_morning_times()

        await bot.send_message(
            USER_ID,
            f"""
🚪 **ПОРА ГОТОВИТЬСЯ К ВЫХОДУ**

Сегодня:

🏫 Первый урок:
**09:00**

🚇 Метро:
выйти примерно
**{morning["metro"]}**

🚗 Машина:
выехать примерно
**{morning["car"]}**

🎒 Проверь:

☑ Телефон
☑ Ключи
☑ Кошелёк
☑ Рюкзак
☑ Нужные тетради
"""
        )

    except Exception as error:

        logger.error(
            "Leave reminder error: %s",
            error
        )


# ============================================================
# SCHEDULER
# ============================================================

def setup_scheduler():

    # --------------------------------------------------------
    # MORNING PLAN
    # --------------------------------------------------------

    scheduler.add_job(
        send_morning_plan,
        "cron",
        day_of_week="mon-fri",
        hour=7,
        minute=30,
        id="morning_plan",
        replace_existing=True
    )

    # --------------------------------------------------------
    # LEAVE REMINDER
    # --------------------------------------------------------

    scheduler.add_job(
        send_leave_reminder,
        "cron",
        day_of_week="mon-fri",
        hour=8,
        minute=0,
        id="leave_reminder",
        replace_existing=True
    )

    # --------------------------------------------------------
    # NIGHT PLAN
    # --------------------------------------------------------

    scheduler.add_job(
        send_night_plan,
        "cron",
        day_of_week="mon-thu",
        hour=21,
        minute=30,
        id="night_plan",
        replace_existing=True
    )

    # --------------------------------------------------------
    # ENGLISH
    # --------------------------------------------------------

    scheduler.add_job(
        send_english_reminder,
        "cron",
        day_of_week="mon-sun",
        hour=19,
        minute=0,
        id="english_reminder",
        replace_existing=True
    )


# ============================================================
# UNKNOWN MESSAGE
# ============================================================

@dp.message()
async def unknown_message(
    message: Message
):

    if not is_allowed(
        message.from_user.id
    ):

        await deny(
            message
        )

        return

    await message.answer(
        """
🤔 Я пока не понял эту команду.

Используй меню ниже 👇
""",
        reply_markup=main_keyboard()
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    logger.info(
        "Starting personal assistant..."
    )

    # database
    await init_db()

    # scheduler
    setup_scheduler()

    scheduler.start()

    # remove old webhook
    await bot.delete_webhook(
        drop_pending_updates=True
    )

    logger.info(
        "Bot started successfully."
    )

    try:

        await dp.start_polling(
            bot
        )

    finally:

        scheduler.shutdown()

        await bot.session.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logger.info(
            "Bot stopped."
        )