# ============================================================
# WordSearchRobot
# Telegram Inline Dictionary Bot
#
# Функционал:
# 1. Работа через Inline Mode:
#       @WordSearchRobot вода
#
# 2. Проверка подписки на @planee_telegram
#
# 3. Если подписки нет:
#       Inline -> Открыть бота -> /start
#
# 4. В личном чате:
#       📢 Подписаться
#       ✅ Проверить подписку
#
# 5. После подписки:
#       🔎 Открыть словарь
#
# 6. Поиск определения через Wikipedia API
# ============================================================


# ============================================================
# ИМПОРТЫ
# ============================================================

import asyncio
import html
import logging
import os
import re
from typing import Optional

import aiohttp

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, Router, F

from aiogram.filters import CommandStart

from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultsButton,
    CallbackQuery,
    Message,
)


# ============================================================
# ЗАГРУЗКА .ENV
# ============================================================

# Загружаем переменные из файла .env.
load_dotenv()


# ============================================================
# НАСТРОЙКИ
# ============================================================

# Получаем токен Telegram-бота.
BOT_TOKEN = os.getenv("BOT_TOKEN")


# Username нашего канала.
CHANNEL_USERNAME = os.getenv(
    "CHANNEL_USERNAME",
    "@planee_telegram"
)


# Ссылка на канал.
CHANNEL_URL = os.getenv(
    "CHANNEL_URL",
    "https://t.me/planee_telegram"
)


# Username бота.
BOT_USERNAME = os.getenv(
    "BOT_USERNAME",
    "WordSearchRobot"
)


# Проверяем наличие токена.
if not BOT_TOKEN:
    raise RuntimeError(
        "❌ BOT_TOKEN не найден в файле .env"
    )


# ============================================================
# ЛОГИРОВАНИЕ
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# ROUTER
# ============================================================

router = Router()


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def clean_word(text: str) -> str:
    """
    Очищает поисковый запрос.

    Например:

        "  вода  "

    превращается в:

        "вода"
    """

    # Убираем пробелы в начале и конце.
    text = text.strip()

    # Заменяем несколько пробелов одним.
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


def escape_html(text: str) -> str:
    """
    Безопасно экранирует HTML.
    """

    return html.escape(
        text,
        quote=False
    )


# ============================================================
# ПРОВЕРКА ПОДПИСКИ
# ============================================================

async def check_subscription(
    bot: Bot,
    user_id: int
) -> Optional[bool]:
    """
    Проверяет подписку пользователя на канал.

    Возвращает:

        True  -> пользователь подписан
        False -> пользователь не подписан
        None  -> произошла ошибка проверки

    ВАЖНО:
    Бот должен быть администратором канала.
    """

    try:

        # Получаем информацию о пользователе
        # внутри нашего канала.
        member = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user_id
        )

        # Получаем статус.
        status = member.status

        # Для диагностики выводим в консоль.
        logger.info(
            "[SUB CHECK] user=%s | status=%s | is_member=%s",
            user_id,
            status,
            getattr(
                member,
                "is_member",
                None
            )
        )

        # Обычный подписчик.
        if status == "member":
            return True

        # Администратор.
        if status == "administrator":
            return True

        # Владелец канала.
        if status == "creator":
            return True

        # Пользователь может быть restricted,
        # но всё ещё состоять в канале.
        if status == "restricted":

            if getattr(
                member,
                "is_member",
                False
            ):
                return True

        # Во всех остальных случаях
        # пользователь не считается подписанным.
        return False

    except Exception as error:

        # Очень важно:
        # ошибка НЕ означает автоматически,
        # что пользователь не подписан.
        logger.exception(
            "[SUB ERROR] user=%s | %s",
            user_id,
            error
        )

        # Возвращаем None,
        # чтобы отличить ошибку от отсутствия подписки.
        return None


# ============================================================
# КЛАВИАТУРА ПОДПИСКИ
# ============================================================

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для личного чата с ботом.

    Кнопки:

        📢 Подписаться
        ✅ Проверить подписку
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[

            # Кнопка открытия канала.
            [
                InlineKeyboardButton(
                    text="📢 Подписаться",
                    url=CHANNEL_URL
                )
            ],

            # Кнопка проверки.
            [
                InlineKeyboardButton(
                    text="✅ Проверить подписку",
                    callback_data="check_subscription"
                )
            ]
        ]
    )


# ============================================================
# КЛАВИАТУРА ПОСЛЕ ПОДПИСКИ
# ============================================================

def get_dictionary_keyboard() -> InlineKeyboardMarkup:
    """
    Кнопка возвращает пользователя
    в Inline Mode.

    Telegram автоматически вставит:

        @WordSearchRobot

    в поле ввода текущего чата.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="🔎 Открыть словарь",
                    switch_inline_query_current_chat=""
                )
            ]

        ]
    )


# ============================================================
# HTTP ЗАПРОС К WIKIPEDIA
# ============================================================

async def wikipedia_request(
    params: dict
) -> dict:
    """
    Выполняет HTTP-запрос к Wikipedia API.
    """

    # Русская Wikipedia.
    url = "https://ru.wikipedia.org/w/api.php"

    # Таймаут запроса.
    timeout = aiohttp.ClientTimeout(
        total=8
    )

    # Создаём HTTP-сессию.
    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        # Выполняем GET-запрос.
        async with session.get(
            url,
            params=params,
            headers={
                "User-Agent":
                    "WordSearchRobot/1.0"
            }
        ) as response:

            # Если сервер вернул ошибку,
            # aiohttp выбросит исключение.
            response.raise_for_status()

            # Получаем JSON.
            return await response.json()


# ============================================================
# ПОЛУЧЕНИЕ СТАТЬИ WIKIPEDIA
# ============================================================

async def get_wikipedia_article(
    title: str
) -> Optional[dict]:
    """
    Получает конкретную статью Wikipedia.
    """

    # Параметры запроса.
    params = {

        # Используем MediaWiki API.
        "action": "query",

        # Ответ в JSON.
        "format": "json",

        # Более удобный формат ответа.
        "formatversion": "2",

        # Получаем текст статьи.
        "prop": "extracts",

        # Ограничиваем длину.
        "exchars": "1000",

        # Получаем обычный текст без HTML.
        "explaintext": "1",

        # Название статьи.
        "titles": title,

        # Учитываем перенаправления.
        "redirects": "1"
    }

    try:

        # Отправляем запрос.
        data = await wikipedia_request(
            params
        )

        # Получаем список страниц.
        pages = (
            data
            .get("query", {})
            .get("pages", [])
        )

        # Если ничего нет.
        if not pages:
            return None

        # Берём первую страницу.
        page = pages[0]

        # Проверяем, существует ли страница.
        if page.get("missing"):
            return None

        # Получаем текст.
        extract = page.get(
            "extract",
            ""
        ).strip()

        # Если текста нет.
        if not extract:
            return None

        # Возвращаем результат.
        return {
            "title": page.get(
                "title",
                title
            ),
            "extract": extract
        }

    except Exception as error:

        logger.exception(
            "[WIKIPEDIA ERROR] %s",
            error
        )

        return None


# ============================================================
# ПОИСК WIKIPEDIA
# ============================================================

async def search_wikipedia(
    word: str
) -> Optional[dict]:
    """
    Ищет слово в Wikipedia.

    Сначала пробуем точное совпадение.

    Если точной статьи нет,
    выполняем обычный поиск.
    """

    # --------------------------------------------------------
    # СНАЧАЛА ИЩЕМ ТОЧНУЮ СТАТЬЮ
    # --------------------------------------------------------

    exact = await get_wikipedia_article(
        word
    )

    # Если нашли точную статью,
    # сразу возвращаем её.
    if exact:
        return exact


    # --------------------------------------------------------
    # ТОЧНОЙ СТАТЬИ НЕТ
    # ИЩЕМ ПО ПОИСКОВОМУ ЗАПРОСУ
    # --------------------------------------------------------

    params = {

        "action": "query",

        "format": "json",

        "formatversion": "2",

        "list": "search",

        # Поисковая строка.
        "srsearch": word,

        # Максимум 5 вариантов.
        "srlimit": "5",

        # Только обычные статьи.
        "srnamespace": "0"
    }

    try:

        # Отправляем запрос.
        data = await wikipedia_request(
            params
        )

        # Получаем результаты.
        results = (
            data
            .get("query", {})
            .get("search", [])
        )

        # Если ничего не нашли.
        if not results:
            return None

        # Берём первый результат.
        first = results[0]

        # Получаем название.
        title = first.get(
            "title"
        )

        # Если название отсутствует.
        if not title:
            return None

        # Получаем полноценную статью.
        return await get_wikipedia_article(
            title
        )

    except Exception as error:

        logger.exception(
            "[WIKIPEDIA SEARCH ERROR] %s",
            error
        )

        return None


# ============================================================
# ФОРМАТИРОВАНИЕ ОПРЕДЕЛЕНИЯ
# ============================================================

def make_definition(
    title: str,
    extract: str
) -> str:
    """
    Делает короткое и понятное определение.

    Максимум 500 символов.
    """

    # Убираем переносы строк.
    text = re.sub(
        r"\s+",
        " ",
        extract
    ).strip()

    # --------------------------------------------------------
    # Пытаемся оставить максимум 2-3 предложения.
    # --------------------------------------------------------

    # Разбиваем текст по предложениям.
    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )

    # Берём максимум 3 предложения.
    sentences = sentences[:3]

    # Собираем обратно.
    text = " ".join(
        sentences
    ).strip()

    # --------------------------------------------------------
    # Ограничиваем 500 символами.
    # --------------------------------------------------------

    if len(text) > 500:

        text = (
            text[:497]
            .rstrip()
            + "..."
        )

    # Экранируем HTML.
    safe_title = escape_html(
        title
    )

    safe_text = escape_html(
        text
    )

    # Формируем итог.
    return (
        f"<b>{safe_title}</b> — "
        f"{safe_text}"
    )


# ============================================================
# /START
# ============================================================

@router.message(
    CommandStart()
)
async def start_handler(
    message: Message,
    bot: Bot
):
    """
    Обработчик команды /start.

    Пользователь попадает сюда,
    когда открывает бота.
    """

    # Получаем ID пользователя.
    user_id = message.from_user.id

    # Проверяем подписку.
    subscribed = await check_subscription(
        bot,
        user_id
    )

    # --------------------------------------------------------
    # ОШИБКА ПРОВЕРКИ
    # --------------------------------------------------------

    if subscribed is None:

        await message.answer(
            "⚠️ <b>Не удалось проверить подписку.</b>\n\n"
            "Попробуйте нажать кнопку "
            "«Проверить подписку» ещё раз.",
            parse_mode="HTML",
            reply_markup=get_subscription_keyboard()
        )

        return


    # --------------------------------------------------------
    # ПОЛЬЗОВАТЕЛЬ УЖЕ ПОДПИСАН
    # --------------------------------------------------------

    if subscribed:

        await message.answer(
            "✅ <b>Вы уже подписаны!</b>\n\n"
            "Теперь вы можете пользоваться "
            "WordSearchRobot.\n\n"
            "🔎 Используйте в любом чате:\n\n"
            "<code>@WordSearchRobot вода</code>\n\n"
            "После этого выберите результат.",
            parse_mode="HTML",
            reply_markup=get_dictionary_keyboard()
        )

        return


    # --------------------------------------------------------
    # ПОЛЬЗОВАТЕЛЬ НЕ ПОДПИСАН
    # --------------------------------------------------------

    await message.answer(
        "🔐 <b>Для работы с WordSearchRobot "
        "нужна подписка.</b>\n\n"
        "Подпишитесь на наш канал, "
        "а затем нажмите "
        "«Проверить подписку».\n\n"
        "После успешной проверки вы сможете "
        "искать значения слов прямо в любом "
        "чате Telegram.",
        parse_mode="HTML",
        reply_markup=get_subscription_keyboard()
    )


# ============================================================
# ПРОВЕРКА ПОДПИСКИ ПО КНОПКЕ
# ============================================================

@router.callback_query(
    F.data == "check_subscription"
)
async def subscription_callback(
    callback: CallbackQuery,
    bot: Bot
):
    """
    Обработчик кнопки:

        ✅ Проверить подписку
    """

    # Получаем пользователя,
    # который нажал кнопку.
    user_id = callback.from_user.id

    # Проверяем подписку.
    subscribed = await check_subscription(
        bot,
        user_id
    )

    # --------------------------------------------------------
    # ОШИБКА
    # --------------------------------------------------------

    if subscribed is None:

        await callback.answer(
            "⚠️ Не удалось проверить подписку. "
            "Попробуйте ещё раз.",
            show_alert=True
        )

        return


    # --------------------------------------------------------
    # ПОЛЬЗОВАТЕЛЬ ЕЩЁ НЕ ПОДПИСАН
    # --------------------------------------------------------

    if not subscribed:

        await callback.answer(
            "❌ Вы ещё не подписались на канал.",
            show_alert=True
        )

        return


    # --------------------------------------------------------
    # ПОДПИСКА ПОДТВЕРЖДЕНА
    # --------------------------------------------------------

    await callback.answer(
        "✅ Подписка подтверждена!",
        show_alert=True
    )

    # Пытаемся заменить старое сообщение.
    try:

        await callback.message.edit_text(

            "🎉 <b>Вы подписались!</b>\n\n"

            "Теперь WordSearchRobot доступен.\n\n"

            "🔎 Чтобы найти значение слова, "
            "напишите в любом чате:\n\n"

            "<code>@WordSearchRobot слово</code>\n\n"

            "Например:\n"

            "<code>@WordSearchRobot вода</code>",

            parse_mode="HTML",

            reply_markup=get_dictionary_keyboard()
        )

    except Exception as error:

        logger.warning(
            "[EDIT ERROR] %s",
            error
        )


# ============================================================
# INLINE MODE
# ============================================================

@router.inline_query()
async def inline_query_handler(
    inline_query: InlineQuery,
    bot: Bot
):
    """
    Главный обработчик Inline Mode.

    Пользователь пишет:

        @WordSearchRobot вода

    Telegram вызывает эту функцию.
    """

    # --------------------------------------------------------
    # Получаем запрос.
    # --------------------------------------------------------

    query = clean_word(
        inline_query.query
    )

    # --------------------------------------------------------
    # ID пользователя.
    # --------------------------------------------------------

    user_id = inline_query.from_user.id

    # Записываем в консоль.
    logger.info(
        "[INLINE] user=%s | query=%r",
        user_id,
        query
    )


    # --------------------------------------------------------
    # ЕСЛИ ПОЛЬЗОВАТЕЛЬ НИЧЕГО НЕ ВВЁЛ
    # --------------------------------------------------------

    if not query:

        await inline_query.answer(

            results=[
                InlineQueryResultArticle(

                    id="help",

                    title="🔎 WordSearchRobot",

                    description=(
                        "Введите слово для поиска."
                    ),

                    input_message_content=
                    InputTextMessageContent(

                        message_text=(
                            "🔎 <b>WordSearchRobot</b>\n\n"
                            "Введите слово для поиска.\n\n"
                            "<code>"
                            "@WordSearchRobot вода"
                            "</code>"
                        ),

                        parse_mode="HTML"
                    )
                )
            ],

            # Результат не нужно долго кэшировать.
            cache_time=1,

            # Результат зависит от конкретного пользователя.
            is_personal=True
        )

        return


    # --------------------------------------------------------
    # ПРОВЕРЯЕМ ПОДПИСКУ
    # --------------------------------------------------------

    subscribed = await check_subscription(
        bot,
        user_id
    )


    # --------------------------------------------------------
    # ОШИБКА ПРОВЕРКИ
    # --------------------------------------------------------

    if subscribed is None:

        # Кнопка открывает личный чат с ботом.
        open_bot_button = InlineQueryResultsButton(

            text="⚠️ Открыть WordSearchRobot",

            # При открытии бота Telegram отправит:
            # /start check_subscription
            start_parameter="check_subscription"
        )

        await inline_query.answer(

            results=[
                InlineQueryResultArticle(

                    id="subscription_check_error",

                    title="⚠️ Не удалось проверить подписку",

                    description=(
                        "Откройте бота и попробуйте ещё раз."
                    ),

                    input_message_content=
                    InputTextMessageContent(

                        message_text=(
                            "⚠️ <b>Не удалось проверить "
                            "подписку.</b>\n\n"
                            "Откройте @WordSearchRobot "
                            "и попробуйте проверить подписку "
                            "ещё раз."
                        ),

                        parse_mode="HTML"
                    )
                )
            ],

            # Эта кнопка появляется сверху
            # над результатами Inline.
            button=open_bot_button,

            cache_time=1,

            is_personal=True
        )

        return


    # --------------------------------------------------------
    # ПОЛЬЗОВАТЕЛЬ НЕ ПОДПИСАН
    # --------------------------------------------------------

    if not subscribed:

        # Создаём кнопку,
        # которая открывает личный чат с ботом.
        open_bot_button = InlineQueryResultsButton(

            text="🔐 Открыть WordSearchRobot",

            # Telegram передаст этот параметр
            # в /start.
            start_parameter="subscribe"
        )

        # Возвращаем результат,
        # но вместо определения показываем инструкцию.
        await inline_query.answer(

            results=[
                InlineQueryResultArticle(

                    id="subscription_required",

                    title="🔐 Требуется подписка",

                    description=(
                        "Подпишитесь на канал "
                        "для использования словаря."
                    ),

                    input_message_content=
                    InputTextMessageContent(

                        message_text=(
                            "🔐 <b>Для использования "
                            "WordSearchRobot нужна подписка.</b>\n\n"
                            "Нажмите кнопку "
                            "«Открыть WordSearchRobot», "
                            "подпишитесь на канал и "
                            "пройдите проверку."
                        ),

                        parse_mode="HTML"
                    )
                )
            ],

            # Кнопка сверху.
            button=open_bot_button,

            # Не кэшируем надолго.
            cache_time=1,

            # Каждый пользователь должен
            # проверяться отдельно.
            is_personal=True
        )

        return


    # ========================================================
    # ПОЛЬЗОВАТЕЛЬ ПОДПИСАН
    # ========================================================

    # Ищем слово в Wikipedia.
    result = await search_wikipedia(
        query
    )


    # --------------------------------------------------------
    # НИЧЕГО НЕ НАШЛИ
    # --------------------------------------------------------

    if not result:

        await inline_query.answer(

            results=[
                InlineQueryResultArticle(

                    id="not_found",

                    title="❌ Ничего не найдено",

                    description=(
                        f'По запросу "{query}" '
                        "ничего не найдено."
                    ),

                    input_message_content=
                    InputTextMessageContent(

                        message_text=(
                            "❌ <b>Ничего не найдено.</b>\n\n"
                            "Попробуйте написать слово "
                            "по-другому."
                        ),

                        parse_mode="HTML"
                    )
                )
            ],

            cache_time=10,

            is_personal=True
        )

        return


    # --------------------------------------------------------
    # ФОРМИРУЕМ ОПРЕДЕЛЕНИЕ
    # --------------------------------------------------------

    title = result["title"]

    extract = result["extract"]

    definition = make_definition(
        title,
        extract
    )


    # --------------------------------------------------------
    # СОЗДАЁМ INLINE-РЕЗУЛЬТАТ
    # --------------------------------------------------------

    article = InlineQueryResultArticle(

        # Уникальный ID результата.
        id=f"word_{abs(hash(title + str(user_id)))}",

        # Название.
        title=f"📖 {title}",

        # Описание в списке Telegram.
        description=extract[:200],

        # Сообщение, которое отправится
        # после нажатия пользователем.
        input_message_content=
        InputTextMessageContent(

            message_text=definition,

            parse_mode="HTML"
        )
    )


    # --------------------------------------------------------
    # ОТПРАВЛЯЕМ РЕЗУЛЬТАТ TELEGRAM
    # --------------------------------------------------------

    await inline_query.answer(

        results=[article],

        # Кэшируем на 30 секунд.
        cache_time=30,

        # Персональный результат.
        is_personal=True
    )


# ============================================================
# ЗАПУСК
# ============================================================

async def main():
    """
    Главная функция запуска.
    """

    # Создаём Telegram Bot.
    bot = Bot(
        token=BOT_TOKEN
    )

    # Создаём Dispatcher.
    dp = Dispatcher()

    # Подключаем Router.
    dp.include_router(
        router
    )

    # Проверяем подключение к Telegram.
    me = await bot.get_me()

    logger.info(
        "=========================================="
    )

    logger.info(
        "WordSearchRobot запущен"
    )

    logger.info(
        "Username: @%s",
        me.username
    )

    logger.info(
        "Channel: %s",
        CHANNEL_USERNAME
    )

    logger.info(
        "=========================================="
    )

    # Запускаем Long Polling.
    await dp.start_polling(
        bot
    )


# ============================================================
# ТОЧКА ВХОДА
# ============================================================

if __name__ == "__main__":

    try:

        # Запускаем бота.
        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        # Корректное завершение.
        logger.info(
            "Бот остановлен."
        )