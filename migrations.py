#!/usr/bin/env python3
"""
Database migration script for OAuth3 TEE Proxy

This script handles database migrations for the OAuth3 TEE Proxy, 
allowing schema changes to be applied incrementally and tracked.

Usage:
  python migrations.py apply
"""

import sys
import logging
import sqlalchemy as sa
from sqlalchemy import create_engine, Column, String, MetaData, Table
from alembic.migration import MigrationContext
from alembic.operations import Operations

from config import get_settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connect to database
settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
conn = engine.connect()
metadata = MetaData()

# Define migration context
context = MigrationContext.configure(conn)
op = Operations(context)

# Define migrations
migrations = []

def add_policy_json_to_twitter_accounts():
    """
    Migration to add policy_json column to twitter_accounts table.
    
    This migration adds a policy_json column to the twitter_accounts table,
    which is used to store access policy configuration for Twitter accounts.
    """
    # Check if the table exists
    inspector = sa.inspect(engine)
    if not "twitter_accounts" in inspector.get_table_names():
        logger.warning("twitter_accounts table does not exist, skipping migration")
        return
    
    # Check if the column already exists
    columns = [c["name"] for c in inspector.get_columns("twitter_accounts")]
    if "policy_json" in columns:
        logger.info("policy_json column already exists in twitter_accounts table")
        return
    
    # Add the column
    logger.info("Adding policy_json column to twitter_accounts table")
    op.add_column("twitter_accounts", Column("policy_json", String, nullable=True))
    logger.info("Added policy_json column to twitter_accounts table")

# Register migrations (in order)
migrations.append(add_policy_json_to_twitter_accounts)

def apply_migrations():
    """
    Apply all registered database migrations.
    
    This function runs each migration in the order they were registered,
    providing a simple mechanism for updating the database schema.
    """
    logger.info(f"Starting database migrations ({len(migrations)} migration(s) registered)")
    
    for migration in migrations:
        logger.info(f"Applying migration: {migration.__name__}")
        migration()
    
    logger.info("Database migrations completed successfully")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "apply":
        apply_migrations()
    else:
        print("Usage: python migrations.py apply")