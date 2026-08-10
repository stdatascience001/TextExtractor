import asyncio
import sys
import os
import traceback
import uuid
from sqlalchemy import text

sys.path.append(r"d:\PdfReader\backendPY")

from sqlalchemy import select
from database.database import SessionLocal, engine
from models.models import Document, ConflictReport
from database.base import Base

async def debug_extraction():
    output_path = r"C:\Users\Admin\.gemini\antigravity-ide\brain\07bf26d0-fb98-4a64-b418-b20124e45d1e\scratch\traceback.txt"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w") as f:
        f.write("Catalog check and extraction debug run started...\n")
        
    try:
        # Check SQLAlchemy metadata columns
        with open(output_path, "a") as f:
            f.write(f"SQLAlchemy model columns in metadata: {[c.name for c in Base.metadata.tables['conflict_reports'].columns]}\n")
            
        async with SessionLocal() as db:
            # Check the columns in the database for conflict_reports
            stmt_catalog = text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'conflict_reports'"
            )
            res_catalog = await db.execute(stmt_catalog)
            cols = res_catalog.all()
            with open(output_path, "a") as f:
                f.write(f"Database columns in conflict_reports: {cols}\n")
                
            # Run the migrator logic inline to capture errors
            with open(output_path, "a") as f:
                f.write("Running inline auto-migrator...\n")
                
            async with engine.begin() as conn:
                for table_name, table in Base.metadata.tables.items():
                    stmt = text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = :table_name"
                    )
                    res = await conn.execute(stmt, {"table_name": table_name})
                    db_columns = {row[0].lower() for row in res.all()}
                    
                    if not db_columns:
                        continue
                        
                    for col in table.columns:
                        col_name_lower = col.name.lower()
                        if col_name_lower not in db_columns:
                            with open(output_path, "a") as f:
                                f.write(f"Detected missing column '{col.name}' in table '{table_name}'. Running ALTER TABLE...\n")
                            
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
                                
                            alter_query = text(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {ddl_type} NULL")
                            await conn.execute(alter_query)
                            with open(output_path, "a") as f:
                                f.write(f"Successfully migrated column '{col.name}' on table '{table_name}'.\n")
            
            # Check the columns again after running migrator
            res_catalog_after = await db.execute(stmt_catalog)
            cols_after = res_catalog_after.all()
            with open(output_path, "a") as f:
                f.write(f"Database columns in conflict_reports after migrator: {cols_after}\n")

            # Load document
            stmt_docs = select(Document).order_by(Document.created_at.desc())
            res_docs = await db.execute(stmt_docs)
            docs = res_docs.scalars().all()
            if not docs:
                with open(output_path, "a") as f:
                    f.write("No documents found in database to run pipeline.\n")
                return
                
            doc = docs[0]
            with open(output_path, "a") as f:
                f.write(f"Running pipeline for latest document: {doc.id} ({doc.file_name})\n")
                
            # Reset status to embedding_completed to force it to run extraction
            doc.status = "embedding_completed"
            await db.commit()
            
            from services.llm_service import ResilientLLMService
            from services.orchestrator import (
                OCRServiceAdapter, ChunkingServiceAdapter, EmbeddingServiceAdapter,
                ExtractionServiceAdapter, ConflictServiceAdapter, ClarificationServiceAdapter
            )
            from services.extraction_service import KnowledgeExtractionEngine
            from services.conflict_service import KnowledgeConflictDetector
            from services.clarification_service import KnowledgeClarificationEngine
            
            llm_service = ResilientLLMService(None)
            
            ocr_service = OCRServiceAdapter()
            chunking_service = ChunkingServiceAdapter()
            embedding_service = EmbeddingServiceAdapter()
            extraction_service = ExtractionServiceAdapter(KnowledgeExtractionEngine(llm_service))
            conflict_service = ConflictServiceAdapter(KnowledgeConflictDetector(llm_service))
            clarification_service = ClarificationServiceAdapter(KnowledgeClarificationEngine(llm_service))

            orchestrator = DocumentOrchestrator(
                ocr_service=ocr_service,
                chunking_service=chunking_service,
                embedding_service=embedding_service,
                extraction_service=extraction_service,
                conflict_service=conflict_service,
                clarification_service=clarification_service
            )
            
            await orchestrator.process_document(db, doc.id, doc.file_path)
            
            with open(output_path, "a") as f:
                f.write("Pipeline run finished successfully!\n")

    except Exception as e:
        tb = traceback.format_exc()
        with open(output_path, "a") as f:
            f.write("Error occurred:\n")
            f.write(tb)
            f.write("\n")

if __name__ == "__main__":
    asyncio.run(debug_extraction())
