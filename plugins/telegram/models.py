# plugins/telegram/models.py
"""
Database models for Telegram plugin
"""

from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base
from models import User


class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    phone_number = Column(String, nullable=False)
    session_string = Column(String, nullable=True)  # Store Telethon session string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="telegram_accounts")
    channels = relationship("TelegramChannel", back_populates="telegram_account")


class TelegramChannel(Base):
    __tablename__ = "telegram_channels"
    
    id = Column(String, primary_key=True)  # Telegram's channel ID
    telegram_account_id = Column(String, ForeignKey("telegram_accounts.id"))
    name = Column(String, nullable=False)
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    telegram_account = relationship("TelegramAccount", back_populates="channels")