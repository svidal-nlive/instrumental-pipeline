# backend/app/routes/song_router.py
from fastapi import APIRouter

song_router = APIRouter()

@song_router.get("/songs", tags=["songs"])
async def list_songs():
    # This is a placeholder. Replace with actual logic to fetch songs.
    return {"message": "List of songs goes here"}
