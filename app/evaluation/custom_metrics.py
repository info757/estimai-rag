"""
Custom evaluation metrics for construction takeoff.

These metrics measure what actually matters for the use case:
- Accurate pipe counts
- Correct material classification  
- Precise elevation extraction
- Effective RAG retrieval
"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class PipeCountAccuracy:
    """Measures if we detected the correct number of pipes."""
    
    @staticmethod
    def evaluate(predicted: Dict[str, Any], expected: Dict[str, Any]) -> float:
        """
        Calculate pipe count accuracy.
        
        Args:
            predicted: Takeoff result
            expected: Ground truth
        
        Returns:
            Score 0.0-1.0 (1.0 = exact match)
        """
        pred_count = predicted.get("summary", {}).get("total_pipes", 0)
        
        expected_pipes = expected.get("expected_pipes", [])
        exp_count = len(expected_pipes)
        
        if exp_count == 0:
            return 1.0 if pred_count == 0 else 0.0
        
        # Exact match = 1.0, each error reduces score
        error_rate = abs(pred_count - exp_count) / exp_count
        score = max(0.0, 1.0 - error_rate)
        
        logger.info(
            f"Pipe Count: predicted={pred_count}, expected={exp_count}, "
            f"accuracy={score:.3f}"
        )
        
        return score


class MaterialAccuracy:
    """Measures if materials were classified correctly."""
    
    @staticmethod
    def evaluate(predicted: Dict[str, Any], expected: Dict[str, Any]) -> float:
        """
        Calculate material classification accuracy.
        
        Returns:
            Score 0.0-1.0 (% of pipes with correct material)
        """
        pred_pipes = predicted.get("pipes", [])
        exp_pipes = expected.get("expected_pipes", [])
        
        if not exp_pipes:
            return 1.0
        
        correct = 0
        total = min(len(pred_pipes), len(exp_pipes))
        
        if total == 0:
            return 0.0
        
        # Simple matching (could be improved with fuzzy matching)
        for i in range(total):
            pred_mat = (pred_pipes[i].get("material") or "").upper()
            exp_mat = (exp_pipes[i].get("material") or "").upper()
            
            if pred_mat in exp_mat or exp_mat in pred_mat:
                correct += 1
        
        score = correct / total
        
        logger.info(
            f"Material: {correct}/{total} correct, accuracy={score:.3f}"
        )
        
        return score


class ElevationAccuracy:
    """Measures if elevations were extracted correctly."""
    
    @staticmethod
    def evaluate(
        predicted: Dict[str, Any],
        expected: Dict[str, Any],
        tolerance_ft: float = 1.0
    ) -> float:
        """
        Calculate elevation extraction accuracy.
        
        Args:
            predicted: Takeoff result
            expected: Ground truth
            tolerance_ft: Tolerance in feet (default ±1 ft)
        
        Returns:
            Score 0.0-1.0 (% of elevations within tolerance)
        """
        pred_pipes = predicted.get("pipes", [])
        exp_pipes = expected.get("expected_pipes", [])
        
        if not exp_pipes:
            return 1.0
        
        correct = 0
        total_elevations = 0
        
        for i, exp_pipe in enumerate(exp_pipes):
            if i >= len(pred_pipes):
                break
            
            pred_pipe = pred_pipes[i]
            
            # Check invert_in
            if exp_pipe.get("invert_in_ft") is not None:
                total_elevations += 1
                pred_ie = pred_pipe.get("invert_in_ft")
                exp_ie = exp_pipe.get("invert_in_ft")
                
                if pred_ie and abs(pred_ie - exp_ie) <= tolerance_ft:
                    correct += 1
            
            # Check invert_out
            if exp_pipe.get("invert_out_ft") is not None:
                total_elevations += 1
                pred_ie_out = pred_pipe.get("invert_out_ft")
                exp_ie_out = exp_pipe.get("invert_out_ft")
                
                if pred_ie_out and abs(pred_ie_out - exp_ie_out) <= tolerance_ft:
                    correct += 1
        
        if total_elevations == 0:
            return 1.0
        
        score = correct / total_elevations
        
        logger.info(
            f"Elevations: {correct}/{total_elevations} within ±{tolerance_ft}ft, "
            f"accuracy={score:.3f}"
        )
        
        return score


class RAGRetrievalQuality:
    """
    Measures if RAG retrieved the expected construction standards.
    
    This is the KEY metric for demonstrating RAG effectiveness.
    """
    
    @staticmethod
    def evaluate(
        retrieved_contexts: List[str],
        expected_keywords: List[str]
    ) -> float:
        """
        Evaluate retrieval quality.
        
        Args:
            retrieved_contexts: List of construction standards retrieved
            expected_keywords: Keywords that should appear in retrieved contexts
        
        Returns:
            Score 0.0-1.0 (% of expected keywords found in contexts)
        """
        if not expected_keywords:
            return 1.0
        
        # Combine all contexts into one text
        all_context_text = " ".join(retrieved_contexts).lower()
        
        # Check how many expected keywords were found
        found = 0
        for keyword in expected_keywords:
            if keyword.lower() in all_context_text:
                found += 1
        
        score = found / len(expected_keywords)
        
        logger.info(
            f"RAG Retrieval: {found}/{len(expected_keywords)} expected keywords found, "
            f"quality={score:.3f}"
        )
        
        return score


def evaluate_takeoff_custom(
    predicted: Dict[str, Any],
    expected: Dict[str, Any],
    retrieved_contexts: List[str]
) -> Dict[str, float]:
    """
    Run all custom metrics on a takeoff result.
    
    Args:
        predicted: Takeoff result from agent
        expected: Ground truth annotations
        retrieved_contexts: Construction standards retrieved via RAG
    
    Returns:
        Dict of metric_name -> score
    """
    scores = {}
    
    # Metric 1: Pipe count
    scores["pipe_count_accuracy"] = PipeCountAccuracy.evaluate(
        predicted, expected
    )
    
    # Metric 2: Materials
    scores["material_accuracy"] = MaterialAccuracy.evaluate(
        predicted, expected
    )
    
    # Metric 3: Elevations
    scores["elevation_accuracy"] = ElevationAccuracy.evaluate(
        predicted, expected, tolerance_ft=1.0
    )
    
    # Metric 4: RAG retrieval (KEY for certification!)
    expected_retrieval = expected.get("expected_retrieval_keywords", [])
    scores["rag_retrieval_quality"] = RAGRetrievalQuality.evaluate(
        retrieved_contexts, expected_retrieval
    )
    
    # Overall average
    scores["overall_accuracy"] = sum(scores.values()) / len(scores)
    
    logger.info(f"Overall Accuracy: {scores['overall_accuracy']:.3f}")
    
    return scores


def format_custom_results_table(scores: Dict[str, float]) -> str:
    """Format custom metrics as markdown table."""
    table = "| Metric | Score | Grade |\n"
    table += "|--------|-------|-------|\n"
    
    for metric, score in scores.items():
        if metric == "overall_accuracy":
            continue
        
        # Grade
        if score >= 0.90:
            grade = "A"
        elif score >= 0.80:
            grade = "B"
        elif score >= 0.70:
            grade = "C"
        else:
            grade = "F"
        
        table += f"| {metric} | {score:.3f} | {grade} |\n"
    
    # Add overall
    overall = scores.get("overall_accuracy", 0.0)
    if overall >= 0.90:
        grade = "A"
    elif overall >= 0.80:
        grade = "B"
    elif overall >= 0.70:
        grade = "C"
    else:
        grade = "F"
    
    table += f"| **Overall** | **{overall:.3f}** | **{grade}** |\n"
    
    return table

