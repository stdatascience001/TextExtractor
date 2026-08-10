import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from database.base import Base

logger = logging.getLogger("db_migrator")

async def run_auto_migrations(engine: AsyncEngine):
    """
    Inspects existing database tables and automatically adds columns
    that exist in the SQLAlchemy models but are missing in the database.
    """
    # Eagerly import all models to register on Base.metadata
    from models.models import (
        User, Project, ProjectMember, Document, DocumentResult, Page, Chunk,
        Embedding, Fact, Evidence, ConflictReport, ClarificationQuestion,
        GeneratedDocument, PromptTemplate, PromptVersion, AIJob, ActivityEvent,
        OutboxMessage, Conversation, Message
    )
    
    logger.info("Running automatic database schema drift migration checks...")
    
    try:
        async with engine.begin() as conn:
            for table_name, table in Base.metadata.tables.items():
                # Query column names for this table in PostgreSQL catalog
                stmt = text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :table_name"
                )
                res = await conn.execute(stmt, {"table_name": table_name})
                db_columns = {row[0].lower() for row in res.all()}
                
                if not db_columns:
                    # Table does not exist yet; metadata.create_all will create it later
                    continue
                    
                for col in table.columns:
                    col_name_lower = col.name.lower()
                    if col_name_lower not in db_columns:
                        logger.warning(f"Detected missing column '{col.name}' in database table '{table_name}'. Running ALTER TABLE...")
                        
                        # Translate SQLAlchemy column types to SQL DDL types
                        sql_type = str(col.type).upper()
                        if "VARCHAR" in sql_type:
                            ddl_type = sql_type
                        elif "UUID" in sql_type:
                            ddl_type = "UUID"
                        elif "TEXT" in sql_type:
                            ddl_type = "TEXT"
                        elif "INTEGER" in sql_type:
                            ddl_type = "INTEGER"
                        elif "FLOAT" in sql_type:
                            ddl_type = "DOUBLE PRECISION"
                        elif "BOOLEAN" in sql_type:
                            ddl_type = "BOOLEAN"
                        elif "TIMESTAMP" in sql_type or "DATETIME" in sql_type:
                            ddl_type = "TIMESTAMP WITH TIME ZONE"
                        elif "JSONB" in sql_type:
                            ddl_type = "JSONB"
                        else:
                            ddl_type = sql_type
                            
                        # Add column as NULL first to avoid constraint violation errors with existing rows
                        alter_query = text(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {ddl_type} NULL")
                        await conn.execute(alter_query)
                        logger.info(f"Successfully migrated column '{col.name}' on table '{table_name}'.")
    except Exception as err:
        logger.error(f"Error during automatic database migrations: {str(err)}")
