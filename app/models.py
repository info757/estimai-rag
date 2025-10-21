"""
Pydantic models for EstimAI-RAG system.

Defines the data structures for agent states, takeoff results, and RAG components.
"""
from typing import Literal, TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage


# ============================================================================
# Agent States (for LangGraph)
# ============================================================================

class AgentState(TypedDict):
    """Main agent state - highest level coordinator."""
    pdf_path: str
    user_query: str
    pdf_summary: str  # What the main agent sees in the PDF
    final_report: dict
    messages: list[BaseMessage]


class SupervisorState(TypedDict, total=False):
    """Supervisor state - task management level."""
    pdf_summary: str  # From main agent
    assigned_tasks: list[dict]  # Tasks for researchers
    researcher_results: dict  # Results from each researcher
    consolidated_data: dict  # Validated, merged results
    conflicts: list[str]  # Any conflicts found between researchers
    vision_result: dict  # Optional: Vision extraction for unknown detection


class ResearcherState(TypedDict):
    """Individual researcher state - execution level."""
    researcher_name: str  # storm, sanitary, water, elevation, legend
    task: str  # Specific task from supervisor
    retrieved_context: list[str]  # RAG-retrieved construction standards
    findings: dict  # What the researcher found


# ============================================================================
# Takeoff Data Models
# ============================================================================

class PipeDetection(BaseModel):
    """A detected pipe with attributes."""
    pipe_id: str
    discipline: Literal["storm", "sanitary", "water"] = Field(
        description="Utility discipline"
    )
    material: str | None = Field(
        default=None,
        description="Pipe material (e.g., PVC, DI, RCP)"
    )
    diameter_in: float | None = Field(
        default=None,
        description="Pipe diameter in inches"
    )
    length_ft: float | None = Field(
        default=None,
        description="Pipe length in feet"
    )
    invert_in_ft: float | None = Field(
        default=None,
        description="Invert elevation at start (feet)"
    )
    invert_out_ft: float | None = Field(
        default=None,
        description="Invert elevation at end (feet)"
    )
    ground_level_ft: float | None = Field(
        default=None,
        description="Ground elevation (feet)"
    )
    depth_ft: float | None = Field(
        default=None,
        description="Pipe depth (ground - invert)"
    )
    # Volume calculations
    excavation_cy: float | None = Field(
        default=None,
        description="Trench excavation volume (cubic yards)"
    )
    bedding_cy: float | None = Field(
        default=None,
        description="Bedding material volume (cubic yards)"
    )
    backfill_cy: float | None = Field(
        default=None,
        description="Backfill volume (cubic yards)"
    )
    compacted_backfill_cy: float | None = Field(
        default=None,
        description="Compacted backfill volume (cubic yards)"
    )
    trench_width_ft: float | None = Field(
        default=None,
        description="Trench width (feet)"
    )
    retrieved_context: list[str] = Field(
        default_factory=list,
        description="RAG context used for this pipe"
    )
    validation_flags: list[str] = Field(
        default_factory=list,
        description="Any validation issues"
    )


class TakeoffSummary(BaseModel):
    """Summary of takeoff results."""
    total_pipes: int
    storm_pipes: int
    sanitary_pipes: int
    water_pipes: int
    storm_lf: float = Field(description="Storm linear feet")
    sanitary_lf: float = Field(description="Sanitary linear feet")
    water_lf: float = Field(description="Water linear feet")
    total_lf: float = Field(description="Total linear feet")
    # Volume totals
    total_excavation_cy: float = Field(default=0.0, description="Total excavation volume (cubic yards)")
    total_bedding_cy: float = Field(default=0.0, description="Total bedding volume (cubic yards)")
    total_backfill_cy: float = Field(default=0.0, description="Total backfill volume (cubic yards)")
    estimated_truck_loads: int = Field(default=0, description="Estimated truck loads (@10 CY/truck)")
    validation_flags_count: int = Field(
        description="Number of validation issues"
    )


class TakeoffResult(BaseModel):
    """Complete takeoff result."""
    summary: TakeoffSummary
    pipes: list[PipeDetection]
    pdf_summary: str = Field(
        description="What the agent understood about the PDF"
    )
    rag_stats: dict = Field(
        default_factory=dict,
        description="RAG retrieval statistics"
    )


# ============================================================================
# RAG Models
# ============================================================================

class ConstructionStandard(BaseModel):
    """A single construction standard/rule."""
    content: str = Field(description="The standard text")
    discipline: Literal["storm", "sanitary", "water", "general"] | None = None
    category: Literal[
        "cover_depth",
        "material",
        "slope",
        "symbol",
        "validation"
    ] | None = None
    source: str = Field(
        description="Source code/standard (e.g., IPC, ASCE, Local Code)"
    )
    reference: str | None = Field(
        default=None,
        description="Specific code section (e.g., IPC 702.1)"
    )


class RAGContext(BaseModel):
    """Retrieved context for a query."""
    query: str
    retrieved_chunks: list[str]
    sources: list[str]
    relevance_scores: list[float]


# ============================================================================
# API Request/Response Models
# ============================================================================

class TakeoffRequest(BaseModel):
    """Request for takeoff."""
    pdf_path: str = Field(description="Path to PDF file")
    user_query: str | None = Field(
        default=None,
        description="Optional user clarification"
    )


class TakeoffResponse(BaseModel):
    """Response from takeoff."""
    result: TakeoffResult
    processing_time_sec: float
    researcher_logs: list[dict] = Field(
        default_factory=list,
        description="Logs from individual researchers (for transparency)"
    )

