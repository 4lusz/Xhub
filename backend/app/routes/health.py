"""Rota de health check -- usada para validar o ambiente de desenvolvimento."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    """Health check simples, sem tocar no banco."""
    return {"status": "ok", "service": "xhub-api"}


@router.get("/health/db")
def health_check_db(db: Session = Depends(get_db)) -> dict:
    """Health check que valida a conexao com o PostgreSQL."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
