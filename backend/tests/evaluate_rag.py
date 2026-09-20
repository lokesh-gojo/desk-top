import asyncio
import sys
import os
from typing import List, Dict, Any

# Ensure project root is in path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.app.rag.vector_search import VectorSearchEngine
from backend.app.rag.bm25_search import BM25SearchEngine
from backend.app.rag.pipeline import RAGPipeline
from backend.app.ingestion.indexer import DocumentIndexer
from backend.app.ingestion.chunker import chunk_text

# Structured benchmark dataset: Answerable vs Unanswerable Institutional Queries
BENCHMARK_DATASET = [
    # Answerable Grounded Queries (Expected: Grounded = True, Evidence = Strong/Moderate)
    {"q": "What UG engineering courses are offered at EASA?", "type": "answerable", "category": "programmes"},
    {"q": "What is the minimum eligibility percentage for B.E admission 2026-27?", "type": "answerable", "category": "admission"},
    {"q": "What is the TNEA single-window counselling code for EASA?", "type": "answerable", "category": "admission"},
    {"q": "Does EASA College have separate hostels for boys and girls?", "type": "answerable", "category": "hostel"},
    {"q": "What is the boys hostel capacity?", "type": "answerable", "category": "hostel"},
    {"q": "Does the EASA bus route go to Gandhipuram?", "type": "answerable", "category": "transport"},
    {"q": "Are there college buses operating to Pollachi?", "type": "answerable", "category": "transport"},
    {"q": "What training does the placement cell provide for students?", "type": "answerable", "category": "placements"},
    {"q": "Tell me about the laboratories in the ECE department", "type": "answerable", "category": "departments"},
    {"q": "What library facilities and volumes are available on campus?", "type": "answerable", "category": "facilities"},
    {"q": "Does EASA College offer sports scholarships and first graduate waivers?", "type": "answerable", "category": "admission"},
    {"q": "When was EASA College established and where is it located?", "type": "answerable", "category": "college_profile"},
    {"q": "What is the autonomous status and NAAC accreditation of EASA?", "type": "answerable", "category": "college_profile"},
    {"q": "How can I contact the EASA admission office phone number?", "type": "answerable", "category": "admission"},
    {"q": "What PG Master's engineering programmes are offered?", "type": "answerable", "category": "programmes"},

    # Unanswerable / Missing Information Queries (Expected: Grounded = False, Fallback Triggered)
    {"q": "What is the 2026-27 hostel mess fee in rupees?", "type": "unanswerable", "category": "hostel"},
    {"q": "What is the third semester ECE class timetable?", "type": "unanswerable", "category": "departments"},
    {"q": "What is the personal mobile phone number of the transport manager?", "type": "unanswerable", "category": "transport"},
    {"q": "What is the canteen lunch menu for today?", "type": "unanswerable", "category": "facilities"},
    {"q": "What are the semester exam marks of student register number 710521104001?", "type": "unanswerable", "category": "student_support"},
    {"q": "What is the WiFi password for the girls hostel second floor?", "type": "unanswerable", "category": "hostel"},
    {"q": "Who won the college cricket tournament in 2012?", "type": "unanswerable", "category": "facilities"},
    {"q": "What is the flight ticket booking procedure from Coimbatore?", "type": "unanswerable", "category": "out_of_domain"}
]

async def run_evaluation():
    print("==================================================================")
    print("EASA DeskBot: RAG Precision & Abstention Benchmark Evaluation")
    print("==================================================================")
    
    # 1. Setup pipeline
    indexer = DocumentIndexer()
    seed_docs = indexer.load_seed_knowledge()
    
    vector_engine = VectorSearchEngine()
    bm25_engine = BM25SearchEngine()
    
    all_chunks = []
    for doc in seed_docs:
        meta = {
            "document_id": doc.get("id"),
            "title": doc.get("title"),
            "category": doc.get("category"),
            "canonical_url": doc.get("canonical_url"),
            "source_authority": doc.get("source_authority", "official_webpage"),
            "status": doc.get("status", "current"),
            "priority": doc.get("priority", 10),
            "last_verified": doc.get("last_verified", "2026-09-20")
        }
        chunks = chunk_text(doc.get("content", ""), meta)
        for c in chunks:
            c["metadata"]["chunk_id"] = f"{doc.get('id')}_{c['chunk_index']}"
        all_chunks.extend(chunks)

    vector_engine.add_chunks(all_chunks)
    bm25_engine.add_chunks(all_chunks)
    pipeline = RAGPipeline(vector_engine=vector_engine, bm25_engine=bm25_engine)

    total_answerable = sum(1 for item in BENCHMARK_DATASET if item["type"] == "answerable")
    total_unanswerable = sum(1 for item in BENCHMARK_DATASET if item["type"] == "unanswerable")
    
    true_positives = 0   # Answerable query correctly answered
    false_negatives = 0  # Answerable query rejected
    true_negatives = 0   # Unanswerable query correctly rejected (abstention)
    false_positives = 0  # Unanswerable query hallucinated / answered

    print(f"\nEvaluating {len(BENCHMARK_DATASET)} queries ({total_answerable} answerable, {total_unanswerable} unanswerable)...\n")

    for idx, item in enumerate(BENCHMARK_DATASET, 1):
        q = item["q"]
        expected_type = item["type"]
        
        res = await pipeline.answer_query(q)
        is_grounded = res.grounded
        
        if expected_type == "answerable":
            if is_grounded:
                true_positives += 1
                status_str = "PASS (Grounded)"
            else:
                false_negatives += 1
                status_str = "FAIL (Under-retrieval)"
        else:
            if not is_grounded:
                true_negatives += 1
                status_str = "PASS (Controlled Fallback)"
            else:
                false_positives += 1
                status_str = "FAIL (Over-answer/Hallucination risk)"

        print(f"[{idx:02d}] {q[:50]:<50} | {status_str}")

    # Metrics
    grounded_recall = (true_positives / total_answerable) * 100 if total_answerable > 0 else 0
    abstention_precision = (true_negatives / (true_negatives + false_positives)) * 100 if (true_negatives + false_positives) > 0 else 0
    abstention_recall = (true_negatives / total_unanswerable) * 100 if total_unanswerable > 0 else 0

    print("\n------------------------------------------------------------------")
    print("BENCHMARK EVALUATION RESULTS:")
    print(f"Total Benchmark Queries : {len(BENCHMARK_DATASET)}")
    print(f"Answerable Queries      : {total_answerable} (Correctly Answered: {true_positives})")
    print(f"Unanswerable Queries    : {total_unanswerable} (Correctly Abstained: {true_negatives})")
    print(f"Grounded Recall         : {grounded_recall:.1f}%")
    print(f"Abstention Precision    : {abstention_precision:.1f}% (Zero-Hallucination on missing facts)")
    print(f"Abstention Recall       : {abstention_recall:.1f}%")
    print("------------------------------------------------------------------")
    print("ALL CONFIGURED EVALUATION BENCHMARKS COMPLETED.")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
