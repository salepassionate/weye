import asyncio
from livekit import api


async def main():
    # Authenticate using the LiveKit environment variables inside Docker.
    client = api.LiveKitAPI()

    try:
        # Request the room list to verify the API credentials.
        await client.room.list_rooms(api.ListRoomsRequest())
        print("LIVEKIT AUTHENTICATION SUCCESSFUL")
    except Exception as error:
        # Report the failure without displaying credentials.
        print(f"LIVEKIT AUTHENTICATION FAILED: {type(error).__name__}: {error}")
    finally:
        # Close the API connection.
        await client.aclose()


# Run the asynchronous authentication test.
asyncio.run(main())
