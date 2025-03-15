# backend/app/admin/routes.py

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import User, Song
from app.auth.routes import get_current_user

admin_router = APIRouter(prefix="/admin", tags=["admin"])

@admin_router.get("/users")
async def list_users(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users

@admin_router.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
    return {"message": f"User {user_id} deleted"}

@admin_router.delete("/songs/{song_id}")
async def delete_song(song_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    result = await db.execute(select(Song).filter(Song.id == song_id))
    song = result.scalars().first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    await db.delete(song)
    await db.commit()
    return {"message": f"Song {song_id} deleted"}
