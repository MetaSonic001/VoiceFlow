"""
/api/users routes — mirrors Express src/routes/users.ts
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import AuthContext, get_auth
from app.models import User

router = APIRouter()


@router.get("/{user_id}")
async def get_user(user_id: str, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id, User.tenantId == auth.tenant_id))
    user = result.scalar_one_or_none()
    if not user:
        return JSONResponse({"error": "User not found"}, status_code=404)
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "createdAt": user.createdAt.isoformat() if user.createdAt else None,
        "updatedAt": user.updatedAt.isoformat() if user.updatedAt else None,
    }
