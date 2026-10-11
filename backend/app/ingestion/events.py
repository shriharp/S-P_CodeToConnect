"""In-process fan-out for live ingestion SSE notifications."""

import asyncio
import json
from dataclasses import dataclass


@dataclass
class LiveEvent:
    event: str
    data: dict

    def encode(self) -> str:
        return f"event: {self.event}\ndata: {json.dumps(self.data, default=str)}\n\n"


class LiveEventHub:
    def __init__(self) -> None:
        self._subscribers: dict[asyncio.Queue[LiveEvent], asyncio.AbstractEventLoop] = {}

    def publish(self, event: str, data: dict) -> None:
        message = LiveEvent(event, data)
        for subscriber, loop in tuple(self._subscribers.items()):
            loop.call_soon_threadsafe(self._offer, subscriber, message)

    def _offer(self, subscriber: asyncio.Queue[LiveEvent], message: LiveEvent) -> None:
        try:
            subscriber.put_nowait(message)
        except asyncio.QueueFull:
            # A disconnected or stalled client must not block ingestion.
            self._subscribers.pop(subscriber, None)

    async def subscribe(self):
        queue: asyncio.Queue[LiveEvent] = asyncio.Queue(maxsize=20)
        self._subscribers[queue] = asyncio.get_running_loop()
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.pop(queue, None)


hub = LiveEventHub()
