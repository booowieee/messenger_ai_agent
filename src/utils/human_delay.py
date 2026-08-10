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
    Simulates human behavior by sending 'typing' action and sleeping
    proportionally to the generated message length.
    """
    min_d = min_delay or settings.DEFAULT_HUMAN_DELAY_MIN
    max_d = max_delay or settings.DEFAULT_HUMAN_DELAY_MAX

    # Base calculation: ~200 chars per minute = ~3.3 chars per second
    calculated_delay = text_length / 25.0  # seconds
    
    # Clamp delay between min_delay and max_delay + random variation
    total_delay = max(min_d, min(calculated_delay, max_d)) + random.uniform(0.5, 1.5)
    
    logger.debug(f"Simulating human typing for chat {chat_id}: {total_delay:.2f}s")
    
    try:
        # Send typing status
        await client.send_chat_action(chat_id, ChatAction.TYPING)
    except Exception as e:
        logger.warning(f"Could not send typing action to chat {chat_id}: {e}")

    await asyncio.sleep(total_delay)
