"""LiveKit voice agent for Weye's demonstration hotel."""
import json
import os
from datetime import date
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, function_tool
from livekit.plugins import cartesia, deepgram, openai, silero

load_dotenv()
API_URL = os.getenv("WEYE_API_URL", "http://localhost:8000")


class HotelAgent(Agent):
    def __init__(self):
        super().__init__(instructions=(
            "You are Weye, a polite hotel reservation voice assistant for a DEMO hotel in Ethiopia. "
            "Speak naturally, briefly, and in English. All prices are Ethiopian birr (ETB). "
            "Ask for check-in date, check-out date, and guest count. Use the availability tool "
            "before mentioning room availability or prices. Do not invent rooms, prices, policies, "
            "or booking references. Before booking, repeat dates, room, guest name, total price "
            "and ask for explicit confirmation. Only after an unambiguous yes, call confirm_booking. "
            "Never promise payment processing or cancellation policies; these are not implemented. "
            "If a tool fails, apologize and recommend speaking to hotel staff. "
            "Never request payment card information. Explain this is a demo if asked."
        ))
        self.last_quote = None
        self.booking_key = None

    @function_tool()
    async def check_availability(self, check_in: str, check_out: str, guests: int) -> str:
        """Look up real demo room inventory. Dates must be ISO YYYY-MM-DD."""
        # Validate ISO dates before making an API request.
        try:
            date.fromisoformat(check_in)
            date.fromisoformat(check_out)
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(f"{API_URL}/availability", json={
                    "check_in": check_in, "check_out": check_out, "guests": guests
                })
                response.raise_for_status()
                result = response.json()
            self.last_quote = {"stay": {"check_in": check_in, "check_out": check_out, "guests": guests}, "rooms": result["rooms"]}
            self.booking_key = None
            return json.dumps(result)
        except (ValueError, httpx.HTTPError) as exc:
            self.last_quote = None
            return f"Availability could not be verified: {exc}"

    @function_tool()
    async def confirm_booking(self, room_type_id: int, guest_name: str, guest_confirmed: bool) -> str:
        """Create a booking ONLY after the guest explicitly agrees to the quoted stay and price."""
        # Never book a room that was not present in the latest verified quote.
        if not guest_confirmed or not self.last_quote:
            return "Cannot book without an availability quote and explicit guest confirmation."
        rooms = self.last_quote["rooms"]
        selected = next((room for room in rooms if room["room_type_id"] == room_type_id), None)
        if selected is None:
            return "That room was not in the latest availability results. Recheck availability."
        if self.booking_key is None:
            self.booking_key = str(uuid4())
        payload = {**self.last_quote["stay"], "room_type_id": room_type_id,
                   "guest_name": guest_name, "idempotency_key": self.booking_key}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(f"{API_URL}/reservations", json=payload)
                response.raise_for_status()
                result = response.json()
            # Clear the quote so another booking requires a new availability check.
            self.last_quote = None
            return json.dumps(result)
        except httpx.HTTPStatusError as exc:
            return f"Booking failed (HTTP {exc.response.status_code}). Do not claim confirmation."
        except httpx.HTTPError:
            return "Booking outcome unknown. Do not retry with a new key; ask staff to verify."


async def entrypoint(ctx: JobContext):
    # Connect to the room first, then start the agent session.
    await ctx.connect()

    session = AgentSession(
        stt=deepgram.STT(model=os.getenv("WEYE_STT_MODEL", "nova-3")),
        llm=openai.LLM(model=os.getenv("WEYE_LLM_MODEL", "gpt-4.1-mini")),
        tts=cartesia.TTS(model=os.getenv("WEYE_TTS_MODEL", "sonic-2024-10-19")),
        vad=silero.VAD.load(),
    )

    await session.start(room=ctx.room, agent=HotelAgent())
    await session.generate_reply(
        instructions="Greet the guest as Weye and ask how you can help with a reservation."
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
