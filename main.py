# ============================================================
# WordSearchRobot
# Telegram Inline Dictionary Bot
# Python + aiogram 3
# ============================================================

# -----------------------------
# Импорт стандартных библиотек
# -----------------------------

import asyncio
import html
import logging
import os
import re

# -----------------------------
# Импорт сторонних библиотек
# -----------------------------

import aiohttp

from dotenv import load_dotenv

# aiogram
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    CallbackQuery,
)

# -----------------------------
# Загружаем переменные .env
# -----------------------------

load_dotenv()

# -----------------------------
# Получаем настройки
# -----------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN")

CHANNEL_USERNAME = os.getenv(
    "CHANNEL_USERNAME",
    "@planee_telegram"
)

CHANNEL_URL = os.getenv(
    "CHANNEL_URL",
    "https://t.me/planee_telegram"
)

# -----------------------------
# Проверяем наличие токена
# -----------------------------

if not BOT_TOKEN:
    raise RuntimeError(
        "Не найден BOT_TOKEN в файле .env"
    )

# -----------------------------
# Настройка логирования
# -----------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

# -----------------------------
# Создаём Router
# -----------------------------

router = Router()

# ============================================================
# Вспомогательные функции
# ============================================================


def clean_word(text: str) -> str:
    """
    Очищает поисковый запрос пользователя.

    Например:

        " вода "
        "ВОДА!!!"
        "что такое вода"

    превращается в более удобный поисковый запрос.
    """

    # Убираем пробелы в начале и конце.
    text = text.strip()

    # Убираем лишние пробелы.
    text = re.sub(r"\s+", " ", text)

    return text


def normalize_word(text: str) -> str:
    """
    Приводит слово к нижнему регистру.

    Используется для сравнения результатов.
    """

    return text.strip().lower()


# ============================================================
# Проверка подписки
# ============================================================


async def check_subscription(
    bot: Bot,
    user_id: int
) -> bool:
    """
    Проверяет, подписан ли пользователь на канал.

    Telegram возвращает объект ChatMember.

    Нас интересуют статусы:

        member
        administrator
        creator

    Также учитываем restricted, если пользователь
    всё ещё является участником канала.
    """

    try:

        # Запрашиваем информацию о пользователе
        # в нашем канале.
        member = await bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=user_id
        )

        # Получаем статус пользователя.
        status = member.status

        logger.info(
            "Проверка подписки: user=%s status=%s",
            user_id,
            status
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

        # В некоторых случаях пользователь
        # может иметь restricted-статус,
        # но при этом оставаться участником.
        if status == "restricted":

            # Проверяем параметр is_member.
            if getattr(member, "is_member", False):
                return True

        # Во всех остальных случаях считаем,
        # что пользователь не подписан.
        return False

    except Exception as error:

        # Записываем ошибку в консоль.
        logger.exception(
            "Ошибка проверки подписки: %s",
            error
        )

        # Безопаснее считать пользователя
        # неподписанным, если Telegram не ответил.
        return False


# ============================================================
# Клавиатура подписки
# ============================================================


def subscription_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру:

    📢 Подписаться
    ✅ Я подписался
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Подписаться",
                    url=CHANNEL_URL
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Я подписался",
                    callback_data="check_subscription"
                )
            ]
        ]
    )


# ============================================================
# Работа с Wikipedia
# ============================================================


async def wikipedia_request(
    params: dict
) -> dict:
    """
    Выполняет запрос к Wikipedia API.
    """

    # Используем русский Wikipedia.
    url = "https://ru.wikipedia.org/w/api.php"

    # Создаём HTTP-сессию.
    timeout = aiohttp.ClientTimeout(total=8)

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        # Отправляем GET-запрос.
        async with session.get(
            url,
            params=params,
            headers={
                "User-Agent":
                    "WordSearchRobot/1.0 Telegram Dictionary Bot"
            }
        ) as response:

            # Проверяем HTTP-код.
            response.raise_for_status()

            # Получаем JSON.
            return await response.json()


async def search_wikipedia(
    word: str
) -> dict | None:
    """
    Ищет статью в русской Wikipedia.

    Сначала пытаемся найти точное совпадение.
    Если его нет — используем поиск.
    """

    # --------------------------------------------------------
    # Шаг 1. Пытаемся получить страницу по точному названию.
    # --------------------------------------------------------

    exact_params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",

        # Получаем краткое описание статьи.
        "prop": "extracts",

        # Максимум около 500 символов.
        "exchars": "500",

        # Без HTML-разметки.
        "explaintext": "1",

        # Ищем конкретную страницу.
        "titles": word,

        # Язык Wikipedia.
        "redirects": "1"
    }

    try:

        data = await wikipedia_request(
            exact_params
        )

        pages = data.get(
            "query",
            {}
        ).get(
            "pages",
            []
        )

        # Если страница существует.
        if pages:

            page = pages[0]

            # В API может быть отрицательный pageid
            # для отсутствующей страницы.
            if not page.get("missing"):

                extract = page.get(
                    "extract",
                    ""
                ).strip()

                if extract:

                    return {
                        "title": page.get(
                            "title",
                            word
                        ),
                        "extract": extract
                    }

    except Exception as error:

        logger.exception(
            "Ошибка точного поиска Wikipedia: %s",
            error
        )

    # --------------------------------------------------------
    # Шаг 2. Если точного совпадения нет,
    # выполняем поиск по Wikipedia.
    # --------------------------------------------------------

    search_params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",

        "list": "search",

        "srsearch": word,

        "srlimit": "5",

        "srnamespace": "0"
    }

    try:

        data = await wikipedia_request(
            search_params
        )

        results = data.get(
            "query",
            {}
        ).get(
            "search",
            []
        )

        # Если результаты найдены.
        if results:

            # Берём первый результат.
            first_result = results[0]

            title = first_result.get(
                "title"
            )

            if title:

                # Теперь получаем полноценную статью.
                return await wikipedia_request_article(
                    title
                )

    except Exception as error:

        logger.exception(
            "Ошибка поиска Wikipedia: %s",
            error
        )

    # Ничего не нашли.
    return None


async def wikipedia_request_article(
    title: str
) -> dict | None:
    """
    Получает короткую выдержку конкретной статьи.
    """

    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",

        "prop": "extracts",

        "exchars": "500",

        "explaintext": "1",

        "titles": title,

        "redirects": "1"
    }

    try:

        data = await wikipedia_request(
            params
        )

        pages = data.get(
            "query",
            {}
        ).get(
            "pages",
            []
        )

        if not pages:
            return None

        page = pages[0]

        extract = page.get(
            "extract",
            ""
        ).strip()

        if not extract:
            return None

        return {
            "title": page.get(
                "title",
                title
            ),
            "extract": extract
        }

    except Exception as error:

        logger.exception(
            "Ошибка получения статьи: %s",
            error
        )

        return None


# ============================================================
# Форматирование определения
# ============================================================


def make_definition(
    title: str,
    extract: str
) -> str:
    """
    Превращает Wikipedia-выдержку
    в короткое определение.

    Ограничиваем текст 500 символами.
    """

    # Убираем переносы строк.
    text = re.sub(
        r"\s+",
        " ",
        extract
    ).strip()

    # Если Wikipedia начала с технического текста,
    # всё равно стараемся сделать короткий ответ.

    # Максимум 500 символов.
    if len(text) > 500:

        # Обрезаем.
        text = text[:497].rstrip() + "..."

    # Экранируем HTML.
    safe_title = html.escape(
        title
    )

    safe_text = html.escape(
        text
    )

    # Финальный формат.
    return (
        f"<b>{safe_title}</b> — "
        f"{safe_text}"
    )


# ============================================================
# Результат для неподписанного пользователя
# ============================================================


def subscription_result() -> InlineQueryResultArticle:
    """
    Возвращает Inline-результат,
    который предлагает подписаться.
    """

    return InlineQueryResultArticle(
        id="subscription_required",

        title="🔒 Требуется подписка",

        description=(
            "Подпишитесь на канал, "
            "чтобы искать слова."
        ),

        input_message_content=InputTextMessageContent(
            message_text=(
                "🔒 <b>Чтобы использовать "
                "WordSearchRobot</b>,\n\n"
                "подпишитесь на наш канал "
                "<b>@planee_telegram</b>."
            ),

            parse_mode="HTML"
        ),

        reply_markup=subscription_keyboard()
    )


# ============================================================
# INLINE HANDLER
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
    # Получаем текст запроса.
    # --------------------------------------------------------

    query = clean_word(
        inline_query.query
    )

    # --------------------------------------------------------
    # Получаем ID пользователя.
    # --------------------------------------------------------

    user_id = inline_query.from_user.id

    logger.info(
        "Inline query: user=%s query=%r",
        user_id,
        query
    )

    # --------------------------------------------------------
    # Если пользователь ничего не ввёл.
    # --------------------------------------------------------

    if not query:

        await inline_query.answer(
            results=[
                InlineQueryResultArticle(
                    id="help",

                    title="🔎 WordSearchRobot",

                    description=(
                        "Введите слово для поиска "
                        "в Wikipedia."
                    ),

                    input_message_content=
                    InputTextMessageContent(
                        message_text=(
                            "🔎 Используйте:\n\n"
                            "<code>"
                            "@WordSearchRobot слово"
                            "</code>"
                        ),
                        parse_mode="HTML"
                    )
                )
            ],

            # Не кэшируем результат надолго.
            cache_time=1,

            # Результат персональный.
            is_personal=True
        )

        return

    # --------------------------------------------------------
    # Проверяем подписку.
    # --------------------------------------------------------

    is_subscribed = await check_subscription(
        bot,
        user_id
    )

    # --------------------------------------------------------
    # Если пользователь НЕ подписан.
    # --------------------------------------------------------

    if not is_subscribed:

        await inline_query.answer(
            results=[
                subscription_result()
            ],

            # Маленький cache_time,
            # чтобы после подписки статус
            # быстро обновился.
            cache_time=1,

            is_personal=True
        )

        return

    # --------------------------------------------------------
    # Пользователь подписан.
    # Начинаем поиск.
    # --------------------------------------------------------

    result = await search_wikipedia(
        query
    )

    # --------------------------------------------------------
    # Wikipedia ничего не нашла.
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
                            f"❌ Не удалось найти "
                            f"определение для "
                            f"<b>{html.escape(query)}</b>."
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
    # Формируем определение.
    # --------------------------------------------------------

    title = result["title"]

    extract = result["extract"]

    definition = make_definition(
        title,
        extract
    )

    # --------------------------------------------------------
    # Создаём результат,
    # который пользователь сможет выбрать.
    # --------------------------------------------------------

    article = InlineQueryResultArticle(
        id=f"word_{abs(hash(title))}",

        # Заголовок результата.
        title=f"📖 {title}",

        # Краткое описание под ним.
        description=extract[:200],

        # Сообщение, которое будет отправлено
        # в текущий чат после нажатия.
        input_message_content=
        InputTextMessageContent(
            message_text=definition,
            parse_mode="HTML"
        )
    )

    # --------------------------------------------------------
    # Отправляем результат Telegram.
    # --------------------------------------------------------

    await inline_query.answer(
        results=[article],

        # Кэшируем недолго.
        cache_time=30,

        # Результаты персональные.
        is_personal=True
    )


# ============================================================
# CALLBACK: "Я подписался"
# ============================================================


@router.callback_query(
    F.data == "check_subscription"
)
async def check_subscription_callback(
    callback: CallbackQuery,
    bot: Bot
):
    """
    Обработчик кнопки:

        ✅ Я подписался

    """

    # Получаем пользователя,
    # который нажал кнопку.
    user_id = callback.from_user.id

    # Проверяем подписку ещё раз.
    is_subscribed = await check_subscription(
        bot,
        user_id
    )

    # --------------------------------------------------------
    # Если подписки всё ещё нет.
    # --------------------------------------------------------

    if not is_subscribed:

        await callback.answer(
            "❌ Вы ещё не подписались на канал.",
            show_alert=True
        )

        return

    # --------------------------------------------------------
    # Подписка подтверждена.
    # --------------------------------------------------------

    await callback.answer(
        "✅ Подписка подтверждена!",
        show_alert=True
    )

    # --------------------------------------------------------
    # Пытаемся изменить сообщение,
    # чтобы убрать предложение подписаться.
    # --------------------------------------------------------

    try:

        await callback.message.edit_text(
            "✅ <b>Подписка подтверждена!</b>\n\n"
            "Теперь вы можете использовать "
            "WordSearchRobot в Inline Mode.\n\n"
            "Например:\n"
            "<code>@WordSearchRobot вода</code>",
            parse_mode="HTML"
        )

    except Exception as error:

        logger.warning(
            "Не удалось изменить сообщение: %s",
            error
        )


# ============================================================
# Запуск бота
# ============================================================


async def main():
    """
    Главная функция запуска.
    """

    # Создаём объект Telegram Bot.
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
        "Бот запущен: @%s",
        me.username
    )

    # Запускаем long polling.
    await dp.start_polling(
        bot
    )


# ============================================================
# Точка входа
# ============================================================


if __name__ == "__main__":

    try:

        # Запускаем asyncio.
        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        # Корректное завершение через Ctrl+C.
        logger.info(
            "Бот остановлен."
        )