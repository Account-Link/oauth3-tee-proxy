#!/usr/bin/env python3
"""
Database Migration Script
========================

This script migrates the database from the old schema to the new schema.
It adds the new tables for JWTToken and AuthAccessLog, and updates the User model.
"""

import logging
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy import Column, String, Boolean, DateTime, MetaData, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship
from sqlalchemy.sql import text

from database import engine, get_db
from models import Base, User, WebAuthnCredential, JWTToken, AuthAccessLog

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrate_tables():
    """Create new tables and migrate data."""
    logger.info("Starting database migration...")
    
    # Create metadata objects
    metadata = MetaData()
    
    # Get current tables from database
    metadata.reflect(bind=engine)
    existing_tables = metadata.tables.keys()
    
    logger.info(f"Existing tables: {', '.join(existing_tables)}")
    
    # Check if new tables need to be created
    new_tables = []
    if "jwt_tokens" not in existing_tables:
        new_tables.append("jwt_tokens")
    if "auth_access_logs" not in existing_tables:
        new_tables.append("auth_access_logs")
    
    # Create new tables
    if new_tables:
        logger.info(f"Creating new tables: {', '.join(new_tables)}")
        Base.metadata.create_all(bind=engine)
        logger.info("New tables created successfully")
    else:
        logger.info("No new tables to create")
    
    # Now check if we need to migrate columns in the users table
    db = next(get_db())
    need_user_update = False
    
    # Check if email column exists
    try:
        db.execute(text("SELECT email FROM users LIMIT 1"))
        logger.info("Email column already exists")
    except:
        need_user_update = True
        logger.info("Email column needs to be added")
    
    # Add columns if needed
    if need_user_update:
        logger.info("Adding new columns to users table")
        try:
            db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR"))
            db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR"))
            db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS wallet_address VARCHAR"))
            db.execute(text("ALTER TABLE users ALTER COLUMN username DROP NOT NULL"))
            logger.info("Users table updated successfully")
        except Exception as e:
            logger.error(f"Error updating users table: {str(e)}")
    
    # Check if webauthn_credentials needs updates
    need_credentials_update = False
    
    # Check if device_name column exists
    try:
        db.execute(text("SELECT device_name FROM webauthn_credentials LIMIT 1"))
        logger.info("device_name column already exists")
    except:
        need_credentials_update = True
        logger.info("device_name column needs to be added")
    
    # Add columns if needed
    if need_credentials_update:
        logger.info("Adding new columns to webauthn_credentials table")
        try:
            db.execute(text("ALTER TABLE webauthn_credentials ADD COLUMN IF NOT EXISTS device_name VARCHAR"))
            db.execute(text("ALTER TABLE webauthn_credentials ADD COLUMN IF NOT EXISTS attestation_type VARCHAR"))
            db.execute(text("ALTER TABLE webauthn_credentials ADD COLUMN IF NOT EXISTS aaguid VARCHAR"))
            db.execute(text("ALTER TABLE webauthn_credentials ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE"))
            logger.info("webauthn_credentials table updated successfully")
        except Exception as e:
            logger.error(f"Error updating webauthn_credentials table: {str(e)}")
    
    # Migrate OAuth2 tokens to JWT tokens if oauth2_tokens table exists
    if "oauth2_tokens" in existing_tables:
        logger.info("Migrating OAuth2 tokens to JWT tokens")
        try:
            # Get all active OAuth2 tokens
            oauth2_tokens = db.execute(text("SELECT * FROM oauth2_tokens WHERE is_active = TRUE")).fetchall()
            logger.info(f"Found {len(oauth2_tokens)} active OAuth2 tokens")
            
            # Convert to JWT tokens
            for token in oauth2_tokens:
                new_token = JWTToken(
                    token_id=token.token_id,
                    user_id=token.user_id,
                    policy="api",
                    scopes=token.scopes,
                    is_active=token.is_active,
                    created_at=token.created_at,
                    expires_at=token.expires_at or (datetime.utcnow() + timedelta(hours=48))
                )
                db.add(new_token)
            
            db.commit()
            logger.info("OAuth2 tokens migrated successfully")
        except Exception as e:
            logger.error(f"Error migrating OAuth2 tokens: {str(e)}")
    
    # Create default device names for existing credentials
    try:
        # Get all credentials without device names
        credentials = db.execute(text("SELECT id FROM webauthn_credentials WHERE device_name IS NULL")).fetchall()
        logger.info(f"Found {len(credentials)} credentials without device names")
        
        for i, cred in enumerate(credentials):
            db.execute(
                text("UPDATE webauthn_credentials SET device_name = :name, is_active = TRUE WHERE id = :id"),
                {"name": f"Device {i+1}", "id": cred.id}
            )
        
        db.commit()
        logger.info("Default device names created")
    except Exception as e:
        logger.error(f"Error creating default device names: {str(e)}")
    
    logger.info("Database migration completed")

if __name__ == "__main__":
    migrate_tables()