"""
RAGAS evaluation pipeline for takeoff system.

Evaluates:
- Faithfulness: Does the agent use retrieved context accurately?
- Answer Relevance: Are the results relevant to the task?
- Context Precision: Are the top retrieved chunks useful?
- Context Recall: Did we retrieve all necessary context?
"""
import logging
from typing import List, Dict, Any
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)

logger = logging.getLogger(__name__)


class RAGASEvaluator:
    """Evaluates takeoff system using RAGAS framework."""
    
    def __init__(self):
        """Initialize RAGAS evaluator."""
        self.metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall
        ]
        logger.info("RAGAS evaluator initialized")
    
    def prepare_dataset(
        self,
        test_cases: List[Dict[str, Any]]
    ) -> Dataset:
        """
        Prepare dataset in RAGAS format.
        
        Args:
            test_cases: List of test cases, each containing:
                - question: The query/task
                - answer: Agent's response
                - contexts: List of retrieved RAG contexts
                - ground_truth: Expected correct answer
        
        Returns:
            Dataset ready for RAGAS evaluation
        """
        logger.info(f"Preparing dataset with {len(test_cases)} test cases")
        
        # Format for RAGAS - each field must be a LIST of values
        dataset_dict = {
            "question": [],
            "answer": [],
            "contexts": [],
            "ground_truth": []
        }
        
        for case in test_cases:
            # Ensure question is string
            question = case.get("question", "")
            if isinstance(question, list):
                question = question[0] if question else ""
            
            # Ensure answer is string
            answer = case.get("answer", "")
            if isinstance(answer, list):
                answer = answer[0] if answer else ""
            
            # Ensure contexts is LIST of strings
            contexts = case.get("contexts", [])
            if not isinstance(contexts, list):
                contexts = [str(contexts)]
            # Make sure each context is a string
            contexts = [str(c) for c in contexts if c]
            if not contexts:
                contexts = ["No context available"]
            
            # Ensure ground_truth is string
            ground_truth = case.get("ground_truth", "")
            if isinstance(ground_truth, list):
                ground_truth = ground_truth[0] if ground_truth else ""
            
            dataset_dict["question"].append(question)
            dataset_dict["answer"].append(answer)
            dataset_dict["contexts"].append(contexts)  # List of strings
            dataset_dict["ground_truth"].append(ground_truth)
        
        dataset = Dataset.from_dict(dataset_dict)
        logger.info("Dataset prepared")
        
        return dataset
    
    def evaluate_takeoff(
        self,
        test_cases: List[Dict[str, Any]],
        metrics: List = None
    ) -> Dict[str, float]:
        """
        Evaluate takeoff results using RAGAS.
        
        Args:
            test_cases: List of test cases
            metrics: Optional custom metrics (defaults to all 4 RAGAS metrics)
        
        Returns:
            Dict of metric_name -> score
        """
        logger.info("Running RAGAS evaluation...")
        
        # Prepare dataset
        dataset = self.prepare_dataset(test_cases)
        
        # Use default or custom metrics
        eval_metrics = metrics or self.metrics
        
        logger.info(f"Evaluating with {len(eval_metrics)} metrics")
        
        try:
            # Run evaluation
            results = evaluate(
                dataset=dataset,
                metrics=eval_metrics
            )
            
            # Convert to pandas and extract ONLY the numeric metric columns
            df = results.to_pandas()
            
            # Get only the metric columns (numeric scores)
            metric_names = [m.name for m in eval_metrics]
            scores = {}
            
            for metric_name in metric_names:
                if metric_name in df.columns:
                    # Calculate mean for this metric
                    scores[metric_name] = float(df[metric_name].mean())
            
            logger.info("RAGAS evaluation complete")
            for metric, score in scores.items():
                logger.info(f"  {metric}: {score:.4f}")
            
            return scores
        
        except Exception as e:
            logger.error(f"RAGAS evaluation failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def create_test_case_from_takeoff(
        self,
        pdf_name: str,
        takeoff_result: Dict[str, Any],
        ground_truth: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a RAGAS test case from a takeoff result.
        
        Args:
            pdf_name: Name of the PDF
            takeoff_result: Results from running takeoff
            ground_truth: Expected correct values
        
        Returns:
            Test case dict ready for RAGAS
        """
        # Extract takeoff_result (the actual data)
        takeoff_data = takeoff_result.get("takeoff_result", {})
        summary = takeoff_data.get("summary", {})
        pipes = takeoff_data.get("pipes", [])
        
        # Extract retrieved contexts from all researchers
        contexts = []
        researcher_results = takeoff_result.get("researcher_results", {})
        for researcher_name, result in researcher_results.items():
            contexts.extend(result.get("retrieved_context", []))
        
        # Remove duplicates and ensure they're strings
        contexts = list(set([str(c) for c in contexts if c]))
        if not contexts:
            contexts = ["No RAG context retrieved"]
        
        # Format answer including researcher analysis (with citations!)
        materials = list(set([p.get('material') for p in pipes if p.get('material')]))
        diameters = list(set([p.get('diameter_in') for p in pipes if p.get('diameter_in')]))
        
        # Get researcher analyses (these should cite standards!)
        researcher_analyses = []
        for researcher_name, result in researcher_results.items():
            findings = result.get("findings", {})
            analysis = findings.get("analysis", "")
            if analysis and len(analysis) > 50:  # Has meaningful content
                researcher_analyses.append(f"**{researcher_name.title()} Researcher Analysis:**\n{analysis[:500]}")
        
        # Combine summary with researcher citations
        answer = f"""Takeoff Results for {pdf_name}:

Summary:
- Total Pipes: {summary.get('total_pipes', 0)}
- Storm: {summary.get('storm_pipes', 0)} pipes, {summary.get('storm_lf', 0):.1f} LF
- Sanitary: {summary.get('sanitary_pipes', 0)} pipes, {summary.get('sanitary_lf', 0):.1f} LF
- Water: {summary.get('water_pipes', 0)} pipes, {summary.get('water_lf', 0):.1f} LF
- Materials: {materials}
- Diameters: {diameters}

Researcher Validation Using Retrieved Standards:
{chr(10).join(researcher_analyses[:2])}"""  # Include up to 2 researcher analyses
        
        # Format ground truth
        gt = ground_truth.get("expected_summary", "")
        if not gt:
            # Build from expected pipes
            expected_pipes = ground_truth.get("expected_pipes", [])
            gt = f"""Expected Results:
Total Pipes: {len(expected_pipes)}
Materials: {list(set(p.get('material', '') for p in expected_pipes))}
Diameters: {list(set(p.get('diameter_in', 0) for p in expected_pipes))}"""
        
        # Question
        question = f"Extract all utility pipes from {pdf_name} including counts, materials, diameters, lengths, and elevations."
        
        return {
            "question": question,
            "answer": answer,
            "contexts": contexts if contexts else ["No RAG context retrieved"],
            "ground_truth": gt
        }
    
    def evaluate_retrieval_quality(
        self,
        query: str,
        retrieved_contexts: List[str],
        expected_contexts: List[str]
    ) -> Dict[str, float]:
        """
        Evaluate retrieval quality directly.
        
        Args:
            query: The retrieval query
            retrieved_contexts: What was actually retrieved
            expected_contexts: What should have been retrieved
        
        Returns:
            Quality metrics
        """
        # Simple precision/recall calculation
        retrieved_set = set(retrieved_contexts)
        expected_set = set(expected_contexts)
        
        if not expected_set:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        
        # How many expected contexts were retrieved?
        overlap = retrieved_set.intersection(expected_set)
        
        precision = len(overlap) / len(retrieved_set) if retrieved_set else 0.0
        recall = len(overlap) / len(expected_set) if expected_set else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "retrieved_count": len(retrieved_set),
            "expected_count": len(expected_set),
            "overlap_count": len(overlap)
        }


def format_results_table(scores: Dict[str, float]) -> str:
    """
    Format RAGAS scores as a markdown table.
    
    Args:
        scores: Dict of metric -> score
    
    Returns:
        Markdown table string
    """
    table = "| Metric | Score |\n"
    table += "|--------|-------|\n"
    
    for metric, score in scores.items():
        table += f"| {metric} | {score:.4f} |\n"
    
    return table


def compare_results_table(
    baseline_scores: Dict[str, float],
    advanced_scores: Dict[str, float]
) -> str:
    """
    Create comparison table for baseline vs advanced.
    
    Args:
        baseline_scores: Scores from baseline retrieval
        advanced_scores: Scores from advanced retrieval
    
    Returns:
        Markdown comparison table
    """
    table = "| Metric | Baseline | Advanced | Improvement |\n"
    table += "|--------|----------|----------|-------------|\n"
    
    for metric in baseline_scores.keys():
        baseline = baseline_scores.get(metric, 0.0)
        advanced = advanced_scores.get(metric, 0.0)
        improvement = advanced - baseline
        improvement_pct = (improvement / baseline * 100) if baseline > 0 else 0
        
        improvement_str = f"{improvement:+.4f} ({improvement_pct:+.1f}%)"
        
        table += f"| {metric} | {baseline:.4f} | {advanced:.4f} | {improvement_str} |\n"
    
    return table

