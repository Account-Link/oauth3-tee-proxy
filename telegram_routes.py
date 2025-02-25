from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import logging
from datetime import datetime

from database import get_db
from models import User, TelegramAccount, TelegramChannel
from telegram_client import TelegramClient

router = APIRouter(prefix="/api/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)

class PhoneNumberRequest(BaseModel):
    phone_number: str

class VerificationRequest(BaseModel):
    phone_number: str
    code: str
    password: Optional[str] = None

class ChannelResponse(BaseModel):
    id: str
    name: str
    username: Optional[str] = None
    participants_count: Optional[int] = None

@router.post("/request-code")
async def request_verification_code(
    request: PhoneNumberRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """Request a verification code for Telegram authentication"""
    try:
        # Check if user is authenticated
        user_id = req.session.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Check if phone number is already registered
        existing_account = db.query(TelegramAccount).filter(
            TelegramAccount.phone_number == request.phone_number
        ).first()
        
        if existing_account and existing_account.user_id != user_id:
            raise HTTPException(
                status_code=400,
                detail="Phone number already registered to another user"
            )

        async with TelegramClient() as client:
            result = await client.request_verification_code(request.phone_number)
            
            # Store data in session for verification
            req.session["telegram_phone"] = request.phone_number
            req.session["telegram_code_hash"] = result["phone_code_hash"]
            req.session["telegram_session"] = result["session_string"]
            
            return {"status": "success"}
    except Exception as e:
        logger.error(f"Error requesting verification code: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify-code")
async def verify_code(
    request: VerificationRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """Verify the Telegram code and create/update account"""
    try:
        # Check if user is authenticated
        user_id = req.session.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Check if we have pending verification
        stored_phone = req.session.get("telegram_phone")
        phone_code_hash = req.session.get("telegram_code_hash")
        session_string = req.session.get("telegram_session")
        
        if not stored_phone or not phone_code_hash or not session_string or stored_phone != request.phone_number:
            raise HTTPException(status_code=400, detail="No pending verification for this phone number")

        async with TelegramClient(session_string) as client:
            # Attempt to sign in
            result = await client.sign_in(
                phone_number=request.phone_number,
                code=request.code,
                phone_code_hash=phone_code_hash,
                password=request.password
            )
            
            # Create or update TelegramAccount
            telegram_account = db.query(TelegramAccount).filter(
                TelegramAccount.phone_number == request.phone_number
            ).first()
            
            if telegram_account:
                telegram_account.session_string = result["session_string"]
                telegram_account.updated_at = datetime.utcnow()
            else:
                telegram_account = TelegramAccount(
                    user_id=user_id,
                    phone_number=request.phone_number,
                    session_string=result["session_string"]
                )
                db.add(telegram_account)
            
            # Clear session data
            req.session.pop("telegram_phone", None)
            req.session.pop("telegram_code_hash", None)
            req.session.pop("telegram_session", None)
            
            db.commit()
            return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error verifying code: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/channels", response_model=List[ChannelResponse])
async def list_channels(
    req: Request,
    db: Session = Depends(get_db)
):
    """List all channels accessible to the user"""
    try:
        # Check if user is authenticated
        user_id = req.session.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Get user's Telegram account
        telegram_account = db.query(TelegramAccount).filter(
            TelegramAccount.user_id == user_id
        ).first()
        
        if not telegram_account:
            raise HTTPException(status_code=404, detail="No Telegram account found")

        # Get channels using stored session
        async with TelegramClient(telegram_account.session_string) as client:
            if not await client.validate_session():
                raise HTTPException(status_code=401, detail="Telegram session expired")
            
            channels = await client.get_channels()
            
            # Update stored channels in database
            existing_channels = {
                channel.id: channel 
                for channel in db.query(TelegramChannel).filter(
                    TelegramChannel.telegram_account_id == telegram_account.id
                ).all()
            }
            
            for channel_data in channels:
                if channel_data["id"] in existing_channels:
                    # Update existing channel
                    channel = existing_channels[channel_data["id"]]
                    channel.name = channel_data["name"]
                    channel.username = channel_data["username"]
                else:
                    # Create new channel
                    channel = TelegramChannel(
                        id=channel_data["id"],
                        telegram_account_id=telegram_account.id,
                        name=channel_data["name"],
                        username=channel_data["username"]
                    )
                    db.add(channel)
            
            db.commit()
            return channels
    except Exception as e:
        logger.error(f"Error listing channels: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) 