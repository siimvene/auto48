"""Reusable FastAPI dependencies declared as Annotated aliases (FastAPI >= 0.95.1)."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auto48.db import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]
