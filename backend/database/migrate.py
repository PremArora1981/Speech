"""Database migration script to create all tables."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.config.settings import settings
from backend.database.models import Base
from backend.utils.logging import get_logger

logger = get_logger(__name__)


def run_migrations():
    """
    Run database migrations to create all tables.

    This will create all tables defined in models.py using SQLAlchemy's
    create_all() method. Tables that already exist will not be modified.
    """
    logger.info("Starting database migrations...")

    # Create engine
    engine = create_engine(str(settings.database_url), echo=True)

    try:
        # Create all tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(engine)
        logger.info("✓ All tables created successfully")

        # Print created tables
        tables = Base.metadata.tables.keys()
        logger.info(f"Created/verified {len(tables)} tables:")
        for table in sorted(tables):
            logger.info(f"  - {table}")

        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False
    finally:
        engine.dispose()


def drop_all_tables():
    """
    Drop all tables (use with caution!).

    WARNING: This will delete all data in the database.
    Only use this in development environments.
    """
    logger.warning("⚠️  DROPPING ALL TABLES - ALL DATA WILL BE LOST!")

    engine = create_engine(str(settings.database_url), echo=True)

    try:
        Base.metadata.drop_all(engine)
        logger.info("✓ All tables dropped successfully")
        return True
    except Exception as e:
        logger.error(f"Drop tables failed: {e}")
        return False
    finally:
        engine.dispose()


def reset_database():
    """Reset database by dropping and recreating all tables."""
    logger.info("Resetting database...")

    if drop_all_tables():
        return run_migrations()
    return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database migration tool")
    parser.add_argument(
        "action",
        choices=["migrate", "reset", "drop"],
        help="Migration action to perform"
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm destructive actions (reset/drop)"
    )

    args = parser.parse_args()

    if args.action == "migrate":
        success = run_migrations()
        sys.exit(0 if success else 1)

    elif args.action == "reset":
        if not args.confirm:
            print("⚠️  WARNING: This will DELETE ALL DATA in the database!")
            print("Use --confirm flag to proceed")
            sys.exit(1)
        success = reset_database()
        sys.exit(0 if success else 1)

    elif args.action == "drop":
        if not args.confirm:
            print("⚠️  WARNING: This will DELETE ALL TABLES in the database!")
            print("Use --confirm flag to proceed")
            sys.exit(1)
        success = drop_all_tables()
        sys.exit(0 if success else 1)
