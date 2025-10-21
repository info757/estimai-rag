"""
Earthwork volume calculations for utility trenches.

Calculates:
- Trench excavation volume
- Bedding material volume
- Backfill volume
- Compaction factors
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TrenchCalculator:
    """Calculate trench excavation and backfill volumes for utility pipes."""
    
    # Standard assumptions (can be overridden)
    WORKING_SPACE = 2.0  # feet on each side of pipe
    BEDDING_DEPTH = 0.5  # feet (6 inches typical)
    COMPACTION_FACTOR = 0.90  # 10% volume loss when compacted
    
    @staticmethod
    def calculate_trench_width(pipe_diameter_in: float) -> float:
        """
        Calculate trench width.
        
        Formula: Pipe Diameter + Working Space
        Standard: Pipe diameter + 2 ft minimum
        
        Args:
            pipe_diameter_in: Pipe diameter in inches
            
        Returns:
            Trench width in feet
        """
        pipe_diameter_ft = pipe_diameter_in / 12.0
        return pipe_diameter_ft + TrenchCalculator.WORKING_SPACE
    
    @staticmethod
    def calculate_pipe_volume(pipe_diameter_in: float, length_ft: float) -> float:
        """
        Calculate volume of pipe itself (to subtract from trench).
        
        Formula: π × r² × L / 27 (convert SF to CY)
        
        Args:
            pipe_diameter_in: Pipe diameter in inches
            length_ft: Pipe length in feet
            
        Returns:
            Pipe volume in cubic yards
        """
        import math
        
        radius_ft = (pipe_diameter_in / 12.0) / 2.0
        area_sf = math.pi * (radius_ft ** 2)
        volume_cf = area_sf * length_ft
        volume_cy = volume_cf / 27.0
        
        return volume_cy
    
    @staticmethod
    def calculate_excavation_volume(
        pipe_diameter_in: float,
        length_ft: float,
        depth_ft: float
    ) -> float:
        """
        Calculate trench excavation volume.
        
        Formula: Width × Depth × Length / 27
        
        Args:
            pipe_diameter_in: Pipe diameter in inches
            length_ft: Pipe length in feet
            depth_ft: Trench depth in feet (ground to invert)
            
        Returns:
            Excavation volume in cubic yards
        """
        width_ft = TrenchCalculator.calculate_trench_width(pipe_diameter_in)
        volume_cf = width_ft * depth_ft * length_ft
        volume_cy = volume_cf / 27.0
        
        return volume_cy
    
    @staticmethod
    def calculate_bedding_volume(
        pipe_diameter_in: float,
        length_ft: float,
        bedding_depth_ft: Optional[float] = None
    ) -> float:
        """
        Calculate bedding material volume.
        
        Bedding: Sand/gravel placed under pipe for support.
        Typical: 6-12 inches
        
        Formula: Width × Bedding Depth × Length / 27
        
        Args:
            pipe_diameter_in: Pipe diameter in inches
            length_ft: Pipe length in feet
            bedding_depth_ft: Bedding depth in feet (default 0.5 ft = 6")
            
        Returns:
            Bedding volume in cubic yards
        """
        if bedding_depth_ft is None:
            bedding_depth_ft = TrenchCalculator.BEDDING_DEPTH
        
        width_ft = TrenchCalculator.calculate_trench_width(pipe_diameter_in)
        volume_cf = width_ft * bedding_depth_ft * length_ft
        volume_cy = volume_cf / 27.0
        
        return volume_cy
    
    @staticmethod
    def calculate_backfill_volume(
        excavation_cy: float,
        pipe_volume_cy: float,
        bedding_cy: float
    ) -> float:
        """
        Calculate backfill volume.
        
        Formula: Excavation - Pipe - Bedding
        
        Args:
            excavation_cy: Total excavation volume (CY)
            pipe_volume_cy: Pipe displacement volume (CY)
            bedding_cy: Bedding material volume (CY)
            
        Returns:
            Backfill volume in cubic yards
        """
        backfill_cy = excavation_cy - pipe_volume_cy - bedding_cy
        return max(0, backfill_cy)  # Can't be negative
    
    @staticmethod
    def calculate_all_volumes(
        pipe_diameter_in: float,
        length_ft: float,
        depth_ft: float,
        bedding_depth_ft: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Calculate all trench volumes for a pipe.
        
        Args:
            pipe_diameter_in: Pipe diameter in inches
            length_ft: Pipe length in feet
            depth_ft: Trench depth in feet
            bedding_depth_ft: Bedding depth in feet (optional)
            
        Returns:
            Dictionary with all volumes:
            {
                "excavation_cy": float,
                "bedding_cy": float,
                "backfill_cy": float,
                "pipe_volume_cy": float,
                "trench_width_ft": float,
                "compacted_backfill_cy": float
            }
        """
        # Calculate each component
        excavation_cy = TrenchCalculator.calculate_excavation_volume(
            pipe_diameter_in, length_ft, depth_ft
        )
        
        bedding_cy = TrenchCalculator.calculate_bedding_volume(
            pipe_diameter_in, length_ft, bedding_depth_ft
        )
        
        pipe_volume_cy = TrenchCalculator.calculate_pipe_volume(
            pipe_diameter_in, length_ft
        )
        
        backfill_cy = TrenchCalculator.calculate_backfill_volume(
            excavation_cy, pipe_volume_cy, bedding_cy
        )
        
        # Apply compaction factor to backfill
        # Need more material to account for compaction
        compacted_backfill_cy = backfill_cy / TrenchCalculator.COMPACTION_FACTOR
        
        trench_width_ft = TrenchCalculator.calculate_trench_width(pipe_diameter_in)
        
        return {
            "excavation_cy": round(excavation_cy, 2),
            "bedding_cy": round(bedding_cy, 2),
            "backfill_cy": round(backfill_cy, 2),
            "compacted_backfill_cy": round(compacted_backfill_cy, 2),
            "pipe_volume_cy": round(pipe_volume_cy, 2),
            "trench_width_ft": round(trench_width_ft, 2)
        }
    
    @staticmethod
    def calculate_from_pipe_data(pipe: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate volumes from pipe detection data.
        
        Uses invert elevations and rim elevations to determine depth.
        Falls back to depth_ft if elevations not available.
        
        Args:
            pipe: Pipe data dict with diameter_in, length_ft, and elevation data
            
        Returns:
            Volume calculations or empty dict if insufficient data
        """
        diameter_in = pipe.get("diameter_in")
        length_ft = pipe.get("length_ft")
        
        if not diameter_in or not length_ft:
            logger.warning("Pipe missing diameter or length, cannot calculate volumes")
            return {}
        
        # Try to calculate depth from elevations
        depth_ft = None
        
        # Method 1: Rim - Invert
        rim_elevation = pipe.get("rim_elevation_ft")
        invert_in = pipe.get("invert_in_ft")
        
        if rim_elevation and invert_in:
            depth_ft = rim_elevation - invert_in
            logger.info(f"Calculated depth from elevations: {depth_ft:.2f} ft (Rim {rim_elevation} - Invert {invert_in})")
        
        # Method 2: Use provided depth_ft
        elif pipe.get("depth_ft"):
            depth_ft = pipe.get("depth_ft")
            logger.info(f"Using provided depth: {depth_ft:.2f} ft")
        
        if not depth_ft or depth_ft <= 0:
            logger.warning("No valid depth available, cannot calculate volumes")
            return {}
        
        # Calculate all volumes
        volumes = TrenchCalculator.calculate_all_volumes(
            pipe_diameter_in=diameter_in,
            length_ft=length_ft,
            depth_ft=depth_ft
        )
        
        logger.info(
            f"Volumes for {diameter_in}\" pipe, {length_ft} LF, {depth_ft:.1f} ft deep: "
            f"Excavation: {volumes['excavation_cy']} CY, "
            f"Bedding: {volumes['bedding_cy']} CY, "
            f"Backfill: {volumes['backfill_cy']} CY"
        )
        
        return volumes


def calculate_project_totals(pipes: list[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate total volumes for all pipes in project.
    
    Args:
        pipes: List of pipe dicts with volume data
        
    Returns:
        Dictionary with project totals
    """
    totals = {
        "total_excavation_cy": 0.0,
        "total_bedding_cy": 0.0,
        "total_backfill_cy": 0.0,
        "total_compacted_backfill_cy": 0.0,
        "total_linear_ft": 0.0,
        "pipes_with_volumes": 0,
        "estimated_truck_loads": 0  # @ 10 CY per truck
    }
    
    for pipe in pipes:
        if pipe.get("excavation_cy"):
            totals["total_excavation_cy"] += pipe.get("excavation_cy", 0)
            totals["total_bedding_cy"] += pipe.get("bedding_cy", 0)
            totals["total_backfill_cy"] += pipe.get("backfill_cy", 0)
            totals["total_compacted_backfill_cy"] += pipe.get("compacted_backfill_cy", 0)
            totals["total_linear_ft"] += pipe.get("length_ft", 0)
            totals["pipes_with_volumes"] += 1
    
    # Estimate truck loads (10 CY per truck typical)
    totals["estimated_truck_loads"] = round(totals["total_excavation_cy"] / 10.0)
    
    # Round totals
    for key in totals:
        if "cy" in key or "ft" in key:
            totals[key] = round(totals[key], 2)
    
    return totals

