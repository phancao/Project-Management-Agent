
import os
import json
import tempfile
import aiofiles
from typing import AsyncIterator, Any, List, Optional
import shutil

class DataBuffer:
    """
    Buffered storage for handling large datasets.
    Writes items to a temporary NDJSON file and allows reading them back.
    """
    def __init__(self, prefix: str = "pm_buffer_"):
        self.temp_dir = tempfile.gettempdir()
        self.fd, self.path = tempfile.mkstemp(prefix=prefix, suffix=".ndjson", dir=self.temp_dir)
        os.close(self.fd)  # Close file descriptor, we'll use aiofiles
        self._count = 0

    async def write_items(self, iterator: AsyncIterator[Any]) -> int:
        """
        Consume an async iterator and write items to the buffer.
        Returns the count of items written.
        """
        def json_serial(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        count = 0
        async with aiofiles.open(self.path, mode='a') as f:
            async for item in iterator:
                # Ensure item is a dict for JSON serialization
                if hasattr(item, "model_dump"):
                    data = item.model_dump()
                elif hasattr(item, "dict"):
                    data = item.dict()
                else:
                    data = item
                
                await f.write(json.dumps(data, default=json_serial) + "\n")
                count += 1
        self._count = count
        return count

    async def read_all(self) -> List[Any]:
        """
        Read all items from the buffer into memory.
        WARNING: Only use this if you know the data fits in memory.
        """
        items = []
        if not os.path.exists(self.path):
            return items
            
        async with aiofiles.open(self.path, mode='r') as f:
            async for line in f:
                if line.strip():
                    items.append(json.loads(line))
        return items

    def cleanup(self):
        """Remove the temporary file."""
        if os.path.exists(self.path):
            try:
                os.remove(self.path)
            except OSError:
                pass
    
    def __del__(self):
        self.cleanup()


async def ensure_async_iterator(data: Any) -> AsyncIterator[Any]:
    """
    Helper to ensure data is an async iterator.
    Handles:
    - AsyncIterator (yields as is)
    - Awaitable Returning List (awaits then yields items)
    - List/Iterable (yields items)
    - Single Item (yields item)
    """
    import inspect
    
    # If it's already an async generator/iterator
    if hasattr(data, "__aiter__"):
        async for item in data:
            yield item
        return

    # If it's an awaitable (coroutine), await it first
    if inspect.isawaitable(data):
        data = await data

    # Now handle the resolved data
    if hasattr(data, "__iter__") and not isinstance(data, (str, bytes)):
        for item in data:
            yield item
    else:
        yield data
