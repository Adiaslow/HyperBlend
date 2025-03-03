"""Command to update the database schema."""

import asyncio
import logging
from datetime import datetime
from sqlalchemy import text, MetaData, Table, Column, DateTime
from sqlalchemy.ext.asyncio import create_async_engine
from hyperblend_old.config import settings
from hyperblend_old.infrastructure.repositories.models.base import Base
from hyperblend_old.management import register_command

logger = logging.getLogger(__name__)


async def get_table_columns(conn, table_name):
    """Get existing columns for a table."""
    # Use SQLite-specific query since we're using SQLite
    result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
    rows = result.fetchall()  # No need to await fetchall() for SQLite
    return {row[1]: row[2] for row in rows}


async def add_timestamp_columns(conn, table_name):
    """Add timestamp columns to an existing table."""
    # Get existing columns
    existing_columns = await get_table_columns(conn, table_name)
    current_time = datetime.utcnow().isoformat()

    # Add created_at if it doesn't exist
    if "created_at" not in existing_columns:
        await conn.execute(
            text(
                f"""
            ALTER TABLE {table_name}
            ADD COLUMN created_at DATETIME;
        """
            )
        )
        await conn.execute(
            text(
                f"""
            UPDATE {table_name}
            SET created_at = :timestamp;
        """
            ),
            {"timestamp": current_time},
        )

    # Add last_updated if it doesn't exist
    if "last_updated" not in existing_columns:
        await conn.execute(
            text(
                f"""
            ALTER TABLE {table_name}
            ADD COLUMN last_updated DATETIME;
        """
            )
        )
        await conn.execute(
            text(
                f"""
            UPDATE {table_name}
            SET last_updated = :timestamp;
        """
            ),
            {"timestamp": current_time},
        )

    # Make columns NOT NULL if they exist
    if "created_at" in existing_columns or "last_updated" in existing_columns:
        await conn.execute(
            text(
                f"""
            CREATE TABLE {table_name}_new AS
            SELECT * FROM {table_name};
        """
            )
        )

        await conn.execute(
            text(
                f"""
            DROP TABLE {table_name};
        """
            )
        )

        await conn.execute(
            text(
                f"""
            CREATE TABLE {table_name} AS
            SELECT * FROM {table_name}_new;
        """
            )
        )

        await conn.execute(
            text(
                f"""
            DROP TABLE {table_name}_new;
        """
            )
        )

    logger.info(f"Added/updated timestamp columns in table {table_name}")


async def add_missing_columns(conn, table_name, table):
    """Add any missing columns to an existing table."""
    # Get existing columns
    existing_columns = await get_table_columns(conn, table_name)

    # Get model columns
    model_columns = {
        name: column
        for name, column in table.columns.items()
        if name
        not in ["id", "created_at", "last_updated"]  # Skip primary key and timestamps
    }

    # Add missing columns
    for name, column in model_columns.items():
        if name not in existing_columns:
            sql_type = str(column.type)
            nullable = "" if column.nullable else "NOT NULL"
            default = ""

            if column.default is not None:
                default = f"DEFAULT {column.default.arg}"

            sql = f"""
                ALTER TABLE {table_name} 
                ADD COLUMN {name} {sql_type} {default} {nullable}
            """
            await conn.execute(text(sql))
            logger.info(f"Added column {name} to table {table_name}")


async def create_missing_tables(conn, metadata):
    """Create any tables that don't exist."""
    # Get existing tables
    result = await conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table'")
    )
    existing_tables = {row[0] for row in result.fetchall()}
    current_time = datetime.utcnow().isoformat()

    # Create missing tables
    for table_name, table in metadata.tables.items():
        if table_name not in existing_tables:
            # Special case for compound_sources table
            if table_name == "compound_sources":
                sql = """
                    CREATE TABLE compound_sources (
                        compound_id VARCHAR NOT NULL,
                        source_id VARCHAR NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        last_updated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (compound_id, source_id),
                        FOREIGN KEY (compound_id) REFERENCES compounds(id),
                        FOREIGN KEY (source_id) REFERENCES sources(id)
                    )
                """
                await conn.execute(text(sql))
                logger.info(f"Created table {table_name}")
                continue

            # Special case for compound_targets table
            if table_name == "compound_targets":
                sql = """
                    CREATE TABLE compound_targets (
                        compound_id VARCHAR NOT NULL,
                        target_id VARCHAR NOT NULL,
                        action VARCHAR,
                        action_type VARCHAR,
                        action_value FLOAT,
                        evidence VARCHAR,
                        evidence_urls VARCHAR,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        last_updated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (compound_id, target_id),
                        FOREIGN KEY (compound_id) REFERENCES compounds(id),
                        FOREIGN KEY (target_id) REFERENCES biological_targets(id)
                    )
                """
                await conn.execute(text(sql))
                logger.info(f"Created table {table_name}")
                continue

            # Get column definitions
            columns = []
            for col in table.columns:
                sql_type = str(col.type)
                nullable = "" if col.nullable else "NOT NULL"
                unique = "UNIQUE" if col.unique else ""
                primary_key = "PRIMARY KEY" if col.primary_key else ""
                default = ""

                # Handle defaults
                if isinstance(col.type, DateTime):
                    if not col.nullable:
                        default = "DEFAULT CURRENT_TIMESTAMP"
                elif col.default is not None:
                    if hasattr(col.default, "arg"):
                        if callable(col.default.arg):
                            # Skip function defaults, they'll be handled in Python
                            pass
                        else:
                            default = f"DEFAULT {col.default.arg}"

                columns.append(
                    f"{col.name} {sql_type} {primary_key} {unique} {nullable} {default}".strip()
                )

            # Create table
            sql = f"""
                CREATE TABLE {table_name} (
                    {', '.join(columns)}
                )
            """
            await conn.execute(text(sql))
            logger.info(f"Created table {table_name}")
        else:
            # Special case for compound_sources table
            if table_name == "compound_sources":
                temp_table = f"{table_name}_temp"

                # Create temp table
                await conn.execute(
                    text(
                        f"""
                    CREATE TABLE {temp_table} AS
                    SELECT * FROM {table_name}
                """
                    )
                )

                # Drop original table
                await conn.execute(
                    text(
                        f"""
                    DROP TABLE {table_name}
                """
                    )
                )

                # Create new table with constraints
                sql = """
                    CREATE TABLE compound_sources (
                        compound_id VARCHAR NOT NULL,
                        source_id VARCHAR NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        last_updated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (compound_id, source_id),
                        FOREIGN KEY (compound_id) REFERENCES compounds(id),
                        FOREIGN KEY (source_id) REFERENCES sources(id)
                    )
                """
                await conn.execute(text(sql))

                # Get column names excluding timestamps
                result = await conn.execute(text(f"PRAGMA table_info({temp_table})"))
                temp_columns = [
                    row[1]
                    for row in result.fetchall()
                    if row[1] not in ["created_at", "last_updated"]
                ]

                # Copy data back excluding timestamps
                sql = f"""
                    INSERT INTO {table_name} ({', '.join(temp_columns)})
                    SELECT {', '.join(temp_columns)}
                    FROM {temp_table}
                """
                await conn.execute(text(sql))

                # Set timestamp values
                await conn.execute(
                    text(
                        f"""
                    UPDATE {table_name}
                    SET created_at = :timestamp,
                        last_updated = :timestamp
                """
                    ),
                    {"timestamp": current_time},
                )

                # Drop temp table
                await conn.execute(
                    text(
                        f"""
                    DROP TABLE {temp_table}
                """
                    )
                )

                logger.info(f"Recreated table {table_name} with constraints")
                continue

            # Special case for compound_targets table
            if table_name == "compound_targets":
                temp_table = f"{table_name}_temp"

                # Create temp table
                await conn.execute(
                    text(
                        f"""
                    CREATE TABLE {temp_table} AS
                    SELECT * FROM {table_name}
                """
                    )
                )

                # Drop original table
                await conn.execute(
                    text(
                        f"""
                    DROP TABLE {table_name}
                """
                    )
                )

                # Create new table with constraints
                sql = """
                    CREATE TABLE compound_targets (
                        compound_id VARCHAR NOT NULL,
                        target_id VARCHAR NOT NULL,
                        action VARCHAR,
                        action_type VARCHAR,
                        action_value FLOAT,
                        evidence VARCHAR,
                        evidence_urls VARCHAR,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        last_updated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (compound_id, target_id),
                        FOREIGN KEY (compound_id) REFERENCES compounds(id),
                        FOREIGN KEY (target_id) REFERENCES biological_targets(id)
                    )
                """
                await conn.execute(text(sql))

                # Get column names excluding timestamps
                result = await conn.execute(text(f"PRAGMA table_info({temp_table})"))
                temp_columns = [
                    row[1]
                    for row in result.fetchall()
                    if row[1] not in ["created_at", "last_updated"]
                ]

                # Copy data back excluding timestamps
                sql = f"""
                    INSERT INTO {table_name} ({', '.join(temp_columns)})
                    SELECT {', '.join(temp_columns)}
                    FROM {temp_table}
                """
                await conn.execute(text(sql))

                # Set timestamp values
                await conn.execute(
                    text(
                        f"""
                    UPDATE {table_name}
                    SET created_at = :timestamp,
                        last_updated = :timestamp
                """
                    ),
                    {"timestamp": current_time},
                )

                # Drop temp table
                await conn.execute(
                    text(
                        f"""
                    DROP TABLE {temp_table}
                """
                    )
                )

                logger.info(f"Recreated table {table_name} with constraints")
                continue

            # Recreate table with constraints
            temp_table = f"{table_name}_temp"

            # Create temp table
            await conn.execute(
                text(
                    f"""
                CREATE TABLE {temp_table} AS
                SELECT * FROM {table_name}
            """
                )
            )

            # Drop original table
            await conn.execute(
                text(
                    f"""
                DROP TABLE {table_name}
            """
                )
            )

            # Create new table with constraints
            columns = []
            for col in table.columns:
                sql_type = str(col.type)
                nullable = "" if col.nullable else "NOT NULL"
                unique = "UNIQUE" if col.unique else ""
                primary_key = "PRIMARY KEY" if col.primary_key else ""
                default = ""

                # Handle defaults
                if isinstance(col.type, DateTime):
                    if not col.nullable:
                        default = "DEFAULT CURRENT_TIMESTAMP"
                elif col.default is not None:
                    if hasattr(col.default, "arg"):
                        if callable(col.default.arg):
                            # Skip function defaults, they'll be handled in Python
                            pass
                        else:
                            default = f"DEFAULT {col.default.arg}"

                columns.append(
                    f"{col.name} {sql_type} {primary_key} {unique} {nullable} {default}".strip()
                )

            sql = f"""
                CREATE TABLE {table_name} (
                    {', '.join(columns)}
                )
            """
            await conn.execute(text(sql))

            # Get column names excluding timestamps
            result = await conn.execute(text(f"PRAGMA table_info({temp_table})"))
            temp_columns = [
                row[1]
                for row in result.fetchall()
                if row[1] not in ["created_at", "last_updated"]
            ]

            # Copy data back excluding timestamps
            sql = f"""
                INSERT INTO {table_name} ({', '.join(temp_columns)})
                SELECT {', '.join(temp_columns)}
                FROM {temp_table}
            """
            await conn.execute(text(sql))

            # Set timestamp values
            await conn.execute(
                text(
                    f"""
                UPDATE {table_name}
                SET created_at = :timestamp,
                    last_updated = :timestamp
            """
                ),
                {"timestamp": current_time},
            )

            # Drop temp table
            await conn.execute(
                text(
                    f"""
                DROP TABLE {temp_table}
            """
                )
            )

            logger.info(f"Recreated table {table_name} with constraints")


async def create_missing_indexes(conn, metadata):
    """Create any missing indexes."""
    # Get existing indexes
    result = await conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='index'")
    )
    existing_indexes = {row[0] for row in result.fetchall()}

    # Create missing indexes
    for table_name, table in metadata.tables.items():
        for index in table.indexes:
            if index.name not in existing_indexes:
                # Get column names and uniqueness
                columns = [col.name for col in index.columns]
                unique = "UNIQUE" if index.unique else ""

                # Create index
                sql = f"""
                    CREATE {unique} INDEX {index.name}
                    ON {table_name} ({', '.join(columns)})
                """
                await conn.execute(text(sql))
                logger.info(f"Created index {index.name}")


async def cleanup_temp_tables(conn):
    """Clean up any temporary tables."""
    # Get all tables
    result = await conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table'")
    )
    tables = {row[0] for row in result.fetchall()}

    # Drop any _temp tables
    for table in tables:
        if table.endswith("_temp"):
            await conn.execute(text(f"DROP TABLE {table}"))
            logger.info(f"Dropped temporary table {table}")


async def update_database():
    """Update the database schema."""
    engine = create_async_engine(settings.DATABASE_URL)
    metadata = Base.metadata

    try:
        async with engine.begin() as conn:
            # Clean up any temporary tables from previous runs
            await cleanup_temp_tables(conn)

            # Create missing tables
            await create_missing_tables(conn, metadata)

            # Add missing columns to existing tables
            for table_name, table in metadata.tables.items():
                await add_missing_columns(conn, table_name, table)
                await add_timestamp_columns(conn, table_name)

            # Create missing indexes
            await create_missing_indexes(conn, metadata)

            logger.info("Database schema updated successfully")
    except Exception as e:
        logger.error(f"Error updating database schema: {str(e)}")
        raise
    finally:
        await engine.dispose()


@register_command("update_database")
def command_update_database(args):
    """Command handler for update_database."""
    try:
        asyncio.run(update_database())
    except Exception as e:
        logger.error(f"Error executing command update_database: {str(e)}")
        raise
