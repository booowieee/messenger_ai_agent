import asyncio
import random
from pyrogram import Client
from pyrogram.enums import ChatAction
from src.config import settings
from src.utils.logger import export_logger as logger


async def simulate_human_response_delay(
    client: Client,
    chat_id: int,
    text_length: int,
    min_delay: float = None,
    max_delay: float = None
):
    """
    Simulates a realistic sequence of human actions:
    1. A small delay before marking message as read (simulating noticing notification).
    2. Marking the chat history as read.
    3. A small delay before starting to type (thinking).
    4. Sending typing indicator in a loop so it stays active until the message is sent.
    """
    # 1. Задержка перед открытием чата (заметил уведомление)
    initial_delay = random.uniform(1.5, 4.0)
    logger.debug(f"Waiting {initial_delay:.2f}s before reading chat {chat_id}")
    await asyncio.sleep(initial_delay)

    # 2. Помечаем чат как прочитанный
    try:
        await client.read_chat_history(chat_id)
        logger.debug(f"Chat {chat_id} marked as read")
    except Exception as e:
        logger.warning(f"Could not mark chat {chat_id} as read: {e}")

    # 3. Задержка перед печатью (осмысление ответа)
    thinking_delay = random.uniform(1.0, 2.5)
    logger.debug(f"Thinking for {thinking_delay:.2f}s before typing in chat {chat_id}")
    await asyncio.sleep(thinking_delay)

    # 4. Имитация набора текста (скорость ~4 знака/сек)
    min_d = min_delay or settings.DEFAULT_HUMAN_DELAY_MIN
    max_d = max_delay or settings.DEFAULT_HUMAN_DELAY_MAX

    calculated_delay = text_length / 4.0
    total_delay = max(min_d, min(calculated_delay, max_d)) + random.uniform(0.5, 1.5)
    
    logger.debug(f"Simulating typing for chat {chat_id}: {total_delay:.2f}s")
    
    # Отправляем статус "печатает" в цикле каждые 4 секунды (Telegram сбрасывает его через 5 сек)
    # Это гарантирует, что статус пропадет ровно в момент прихода сообщения.
    elapsed = 0.0
    while elapsed < total_delay:
        try:
            await client.send_chat_action(chat_id, ChatAction.TYPING)
        except Exception as e:
            logger.warning(f"Could not send typing action: {e}")
            
        sleep_chunk = min(4.0, total_delay - elapsed)
        await asyncio.sleep(sleep_chunk)
        elapsed += sleep_chunk
