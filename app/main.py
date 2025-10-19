"""
FastAPI application for EstimAI-RAG.

Main endpoint: POST /takeoff - upload PDF and get takeoff results
"""
import logging
import time
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.models import TakeoffResponse
from app.agents.main_agent import run_takeoff

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="EstimAI-RAG",
    description="AI-Powered Construction Takeoff with Multi-Agent RAG",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "app": "EstimAI-RAG",
        "version": "1.0.0",
        "description": "Multi-Agent RAG for Construction Takeoff",
        "endpoints": {
            "health": "/health",
            "takeoff": "/takeoff (POST)",
            "docs": "/docs"
        }
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "components": {
            "api": "ok",
            "qdrant": "check manually",
            "openai": "check manually"
        }
    }


class SimpleRequest(BaseModel):
    """Simple request for testing."""
    pdf_path: str
    user_query: str = ""


@app.post("/takeoff/simple")
def takeoff_simple(request: SimpleRequest):
    """
    Simple takeoff endpoint (for testing with existing PDF).
    
    Args:
        request: PDF path and optional query
    
    Returns:
        Takeoff results
    """
    start_time = time.time()
    
    logger.info(f"Simple takeoff request: {request.pdf_path}")
    
    try:
        # Run takeoff
        result = run_takeoff(
            pdf_path=request.pdf_path,
            user_query=request.user_query
        )
        
        processing_time = time.time() - start_time
        
        # Extract researcher logs
        researcher_logs = []
        if "researcher_results" in result:
            for name, res in result["researcher_results"].items():
                researcher_logs.append({
                    "researcher": name,
                    "confidence": res.get("confidence", 0.0),
                    "findings_summary": str(res.get("findings", {}))[:200]
                })
        
        return {
            "result": result.get("takeoff_result", result.get("consolidated_data", {})),
            "processing_time_sec": processing_time,
            "researcher_logs": researcher_logs
        }
    
    except Exception as e:
        logger.error(f"Takeoff failed: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "error": str(e),
            "result": None,
            "processing_time_sec": time.time() - start_time
        }


@app.post("/takeoff")
async def takeoff(
    file: UploadFile = File(...),
    user_query: str = Form(default="")
):
    """
    Main takeoff endpoint - upload PDF and get results.
    
    Args:
        file: PDF file upload
        user_query: Optional clarification
    
    Returns:
        Takeoff results with RAG context
    """
    start_time = time.time()
    
    logger.info(f"Takeoff request: {file.filename}")
    
    try:
        # Save uploaded file
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"Saved to: {file_path}")
        
        # Run takeoff
        result = run_takeoff(
            pdf_path=str(file_path),
            user_query=user_query
        )
        
        processing_time = time.time() - start_time
        
        # Extract researcher logs for transparency
        researcher_logs = []
        if "researcher_results" in result:
            for name, res in result["researcher_results"].items():
                researcher_logs.append({
                    "researcher": name,
                    "task": res.get("task", ""),
                    "confidence": res.get("confidence", 0.0),
                    "standards_used": len(res.get("retrieved_context", [])),
                    "findings_summary": str(res.get("findings", {}))[:200] + "..."
                })
        
        # Extract user alerts if present (from consolidated_data)
        consolidated = result.get("consolidated_data", {})
        user_alerts = consolidated.get("user_alerts")
        
        logger.info(
            f"Takeoff complete: {processing_time:.2f}s, "
            f"{len(researcher_logs)} researchers deployed"
        )
        
        if user_alerts:
            logger.warning(f"User alerts: {user_alerts.get('severity')} - {user_alerts.get('total_unknowns')} unknowns")
        
        return {
            "filename": file.filename,  # For PDF viewer
            "result": result.get("takeoff_result", result.get("consolidated_data", {})),
            "user_alerts": user_alerts,  # Critical for HITL
            "researcher_results": result.get("researcher_results", {}),
            "processing_time_sec": processing_time,
            "researcher_logs": researcher_logs
        }
    
    except Exception as e:
        logger.error(f"Takeoff failed: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "error": str(e),
            "result": None,
            "processing_time_sec": time.time() - start_time,
            "researcher_logs": []
        }


@app.get("/uploads/{filename}")
async def serve_pdf(filename: str):
    """Serve uploaded PDF for viewing in browser."""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(
        file_path,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

