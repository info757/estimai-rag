#!/usr/bin/env python3
"""
Simple RAGAS evaluation using live backend.

Tests RAG retrieval quality on construction standards questions.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import subprocess
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    context_precision,
    context_recall,
    faithfulness,
    answer_relevancy
)

# Test cases for RAG evaluation
# These test if our RAG retrieves the right construction standards
TEST_CASES = [
    {
        "question": "What is the minimum cover depth for RCP storm drain pipes?",
        "ground_truth": "3.0 feet for H-20 loading",
        "expected_context_keywords": ["RCP", "cover", "3.0 feet", "H-20"]
    },
    {
        "question": "What materials are approved for sanitary sewer pipes?",
        "ground_truth": "PVC and HDPE are suitable. RCP susceptible to sulfide attack.",
        "expected_context_keywords": ["PVC", "HDPE", "sanitary", "sulfide"]
    },
    {
        "question": "What is the minimum cover for water mains under roadways?",
        "ground_truth": "4.5 feet minimum under roadways",
        "expected_context_keywords": ["water main", "4.5 feet", "roadway"]
    },
    {
        "question": "What does the CB symbol indicate on construction plans?",
        "ground_truth": "Catch basin for storm drainage",
        "expected_context_keywords": ["CB", "catch basin", "storm"]
    },
    {
        "question": "What is the minimum slope for 12 inch storm drain pipes?",
        "ground_truth": "0.5% for pipes 8-12 inches",
        "expected_context_keywords": ["storm", "slope", "0.5%", "12"]
    }
]


def query_rag_directly(question):
    """Query RAG retrieval system directly."""
    from app.rag.retriever import HybridRetriever
    from langchain_openai import ChatOpenAI
    
    retriever = HybridRetriever()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Retrieve context
    results = retriever.retrieve_hybrid(question, k=5)
    contexts = [r['content'] for r in results]
    
    # Generate answer using LLM + RAG context
    context_text = "\n\n".join([f"Standard {i+1}: {ctx}" for i, ctx in enumerate(contexts)])
    prompt = f"""Based on these construction standards, answer the question.

Construction Standards:
{context_text}

Question: {question}

Provide a concise, factual answer based only on the standards provided."""
    
    response = llm.invoke(prompt)
    answer = response.content
    
    return {
        "contexts": contexts,
        "answer": answer
    }


def main():
    print("\n" + "="*70)
    print("RAGAS EVALUATION - RAG Retrieval Quality")
    print("="*70)
    
    print(f"\n📚 Evaluating {len(TEST_CASES)} construction standards questions")
    
    # Prepare RAGAS dataset
    ragas_data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": []
    }
    
    print("\n🔍 Querying RAG system...")
    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n  {i}. {test['question']}")
        
        try:
            result = query_rag_directly(test['question'])
            
            ragas_data["question"].append(test['question'])
            ragas_data["answer"].append(result['answer'])
            ragas_data["contexts"].append(result['contexts'])
            ragas_data["ground_truth"].append(test['ground_truth'])
            
            print(f"     ✓ Retrieved {len(result['contexts'])} contexts")
            
        except Exception as e:
            print(f"     ✗ Failed: {e}")
    
    print(f"\n✅ Prepared {len(ragas_data['question'])} test cases for RAGAS")
    
    # Create dataset
    dataset = Dataset.from_dict(ragas_data)
    
    # Run RAGAS evaluation
    print("\n📊 Running RAGAS evaluation...")
    print("   This will measure:")
    print("   - Context Precision: Are top results relevant?")
    print("   - Context Recall: Did we retrieve all necessary info?")
    print("   - Faithfulness: Is answer grounded in context?")
    print("   - Answer Relevancy: Does answer address question?")
    
    try:
        results = evaluate(
            dataset,
            metrics=[
                context_precision,
                context_recall,
                faithfulness,
                answer_relevancy
            ]
        )
        
        print("\n" + "="*70)
        print("RAGAS EVALUATION RESULTS")
        print("="*70)
        
        scores = results.to_pandas()
        print("\n📈 Overall Scores:")
        for metric in ["context_precision", "context_recall", "faithfulness", "answer_relevancy"]:
            if metric in scores.columns:
                avg_score = scores[metric].mean()
                print(f"   {metric:20s}: {avg_score:.4f} ({avg_score*100:.1f}%)")
        
        # Save results
        output_file = "golden_dataset/ragas_results.json"
        
        # Extract only numeric metric columns
        metric_columns = [col for col in scores.columns 
                         if col not in ["question", "answer", "contexts", "ground_truth", "user_input", "response", "retrieved_contexts", "reference"]]
        
        results_dict = {
            "overall_scores": {
                metric: float(scores[metric].mean()) 
                for metric in metric_columns
            },
            "test_cases_count": len(scores),
            "evaluation_date": "2025-10-19",
            "per_question_results": [
                {
                    "question": row.get("question", ""),
                    **{metric: row.get(metric, 0.0) for metric in metric_columns}
                }
                for _, row in scores.iterrows()
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        
        print("\n" + "="*70)
        print("✅ RAGAS EVALUATION COMPLETE")
        print("="*70)
        print("\n📋 For Certification:")
        print("   - RAG retrieval quality measured")
        print("   - Results saved in golden_dataset/")
        print("   - Ready for Tuesday submission\n")
        
    except Exception as e:
        print(f"\n❌ RAGAS evaluation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

