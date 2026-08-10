import time
import json
import asyncio
import logging
from typing import AsyncIterator, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("stream_manager")

class StreamingMetrics(BaseModel):
    time_to_first_token_ms: float = 0.0
    tokens_per_second: float = 0.0
    total_tokens: int = 0
    total_duration_seconds: float = 0.0

class StreamManager:
    @staticmethod
    def format_sse(data: Any, event_name: Optional[str] = None) -> str:
        """Formats data payload as Server-Sent Event (SSE) block."""
        payload = json.dumps(data)
        if event_name:
            return f"event: {event_name}\ndata: {payload}\n\n"
        return f"data: {payload}\n\n"

    @staticmethod
    def format_ndjson(data: Any) -> str:
        """Formats data payload as line-delimited JSON (NDJSON) line."""
        return json.dumps(data) + "\n"

    async def heartbeat_generator(self, interval_seconds: float = 10.0, mode: str = "ndjson") -> AsyncIterator[str]:
        """Periodically yields ping heartbeat keep-alives to prevent timeout disconnects."""
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                ping_payload = {"type": "ping", "timestamp": time.time()}
                if mode == "sse":
                    yield self.format_sse(ping_payload, "ping")
                else:
                    yield self.format_ndjson(ping_payload)
            except asyncio.CancelledError:
                break

    async def iterate_stream(
        self,
        token_generator: AsyncIterator[str],
        mode: str = "ndjson"
    ) -> AsyncIterator[str]:
        """
        Iterates over a stream of token strings, tracking throughput speed metrics,
        detecting client cancellations, and formatting outputs as SSE or NDJSON.
        """
        start_time = time.time()
        ttft_recorded = False
        ttft_ms = 0.0
        token_count = 0

        try:
            async for token in token_generator:
                current_time = time.time()
                
                # TTFT (Time to First Token) Calculation
                if not ttft_recorded:
                    ttft_ms = (current_time - start_time) * 1000
                    ttft_recorded = True

                token_count += 1
                
                # Format payload
                data_payload = {
                    "type": "token",
                    "content": token,
                    "index": token_count
                }
                
                if mode == "sse":
                    yield self.format_sse(data_payload, "message")
                else:
                    yield self.format_ndjson(data_payload)

            # Stream complete - calculate final performance metrics
            duration = time.time() - start_time
            throughput = (token_count / duration) if duration > 0 else 0.0
            
            metrics = StreamingMetrics(
                time_to_first_token_ms=round(ttft_ms, 2),
                tokens_per_second=round(throughput, 2),
                total_tokens=token_count,
                total_duration_seconds=round(duration, 3)
            )
            
            summary_payload = {
                "type": "metrics",
                "metrics": metrics.model_dump()
            }
            
            if mode == "sse":
                yield self.format_sse(summary_payload, "metrics")
            else:
                yield self.format_ndjson(summary_payload)

        except asyncio.CancelledError:
            logger.info("StreamManager detected client connection cancellation. Stopping generator.")
            raise
        except Exception as e:
            logger.error(f"StreamManager encountered error during iteration: {str(e)}")
            error_payload = {"type": "error", "message": str(e)}
            if mode == "sse":
                yield self.format_sse(error_payload, "error")
            else:
                yield self.format_ndjson(error_payload)

    async def handle_websocket_loop(
        self,
        websocket: Any,
        token_generator: AsyncIterator[str],
        heartbeat_interval: float = 10.0
    ):
        """Manages WebSocket connection send loops with Heartbeat keep-alives and cancellations."""
        start_time = time.time()
        token_count = 0
        ttft_recorded = False
        ttft_ms = 0.0

        async def send_heartbeats():
            while True:
                try:
                    await asyncio.sleep(heartbeat_interval)
                    await websocket.send_json({"type": "ping", "timestamp": time.time()})
                except Exception:
                    break

        # Spawn heartbeat loop in background
        heartbeat_task = asyncio.create_task(send_heartbeats())

        try:
            async for token in token_generator:
                current_time = time.time()
                if not ttft_recorded:
                    ttft_ms = (current_time - start_time) * 1000
                    ttft_recorded = True

                token_count += 1
                await websocket.send_json({
                    "type": "token",
                    "content": token,
                    "index": token_count
                })

            duration = time.time() - start_time
            throughput = (token_count / duration) if duration > 0 else 0.0
            
            # Send final metrics
            await websocket.send_json({
                "type": "metrics",
                "metrics": {
                    "time_to_first_token_ms": round(ttft_ms, 2),
                    "tokens_per_second": round(throughput, 2),
                    "total_tokens": token_count,
                    "total_duration_seconds": round(duration, 3)
                }
            })

        except Exception as e:
            logger.error(f"WebSocket streaming loop crashed: {str(e)}")
            try:
                await websocket.send_json({"type": "error", "message": str(e)})
            except Exception:
                pass
        finally:
            heartbeat_task.cancel()
