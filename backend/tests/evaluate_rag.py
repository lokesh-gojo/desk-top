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
from backend.app.models.schema import Message

# Comprehensive Benchmark Dataset: English, Tamil, Tanglish, and Unanswerable queries
BENCHMARK_DATASET = [
    # 1. English Answerable Factual Queries
    {
        "q": "What UG engineering courses are offered at EASA?",
        "type": "answerable",
        "lang": "en",
        "category": "programmes",
        "expected_facts": ["Computer Science", "B.E", "B.Tech"]
    },
    {
        "q": "What is the minimum eligibility percentage for B.E admission 2026-27?",
        "type": "answerable",
        "lang": "en",
        "category": "admission",
        "expected_facts": ["45%", "40%"]
    },
    {
        "q": "What is the TNEA single-window counselling code for EASA College?",
        "type": "answerable",
        "lang": "en",
        "category": "admission",
        "expected_facts": ["2755"]
    },
    {
        "q": "What is the boys hostel capacity at EASA?",
        "type": "answerable",
        "lang": "en",
        "category": "hostel",
        "expected_facts": ["250"]
    },
    {
        "q": "Does the EASA college bus route go to Gandhipuram?",
        "type": "answerable",
        "lang": "en",
        "category": "transport",
        "expected_facts": ["Gandhipuram"]
    },
    {
        "q": "Tell me about the laboratories in the ECE department",
        "type": "answerable",
        "lang": "en",
        "category": "departments",
        "expected_facts": ["VLSI", "DSP", "ECE"]
    },
    {
        "q": "When was EASA College established and what is its accreditation?",
        "type": "answerable",
        "lang": "en",
        "category": "college_profile",
        "expected_facts": ["2008", "NAAC", "Autonomous"]
    },

    # 2. Native Tamil (தமிழ்) Queries
    {
        "q": "ஈசாவில் என்னென்ன UG courses உள்ளன?",
        "type": "answerable",
        "lang": "ta",
        "category": "programmes",
        "expected_facts": ["B.E", "Computer Science", "B.Tech"]
    },
    {
        "q": "காந்திபுரம் பஸ் இருக்கா?",
        "type": "answerable",
        "lang": "ta",
        "category": "transport",
        "expected_facts": ["Gandhipuram"]
    },
    {
        "q": "ஹாஸ்டல் வசதிகள் என்ன?",
        "type": "answerable",
        "lang": "ta",
        "category": "hostel",
        "expected_facts": ["Hostel", "250", "Wi-Fi"]
    },

    # 3. Code-Mixed Tanglish Student Queries
    {
        "q": "EASA la ECE department details என்ன?",
        "type": "answerable",
        "lang": "ta",
        "category": "departments",
        "expected_facts": ["ECE", "Electronics"]
    },
    {
        "q": "College bus Pollachi route ku poguma?",
        "type": "answerable",
        "lang": "ta",
        "category": "transport",
        "expected_facts": ["Pollachi"]
    },

    # 4. Conversational Contextual Follow-up Query
    {
        "q": "What about ECE?",
        "type": "answerable",
        "lang": "en",
        "category": "departments",
        "history": [
            Message(role="user", content="What UG courses are available?"),
            Message(role="assistant", content="EASA offers 10 UG programmes including CSE, ECE, EEE, Mech.")
        ],
        "expected_facts": ["ECE", "Electronics"]
    },

    # 5. Unanswerable / Unsupported Queries (Expected: Strict Abstention via Controlled Fallback)
    {
        "q": "What is the 2026-27 hostel mess fee in rupees?",
        "type": "unanswerable",
        "lang": "en",
        "category": "hostel"
    },
    {
        "q": "What is the third semester ECE class timetable?",
        "type": "unanswerable",
        "lang": "en",
        "category": "departments"
    },
    {
        "q": "What is the personal phone number of the transport manager?",
        "type": "unanswerable",
        "lang": "en",
        "category": "transport"
    },
    {
        "q": "What are the semester exam marks of student register number 710521104001?",
        "type": "unanswerable",
        "lang": "en",
        "category": "student_support"
    },
    {
        "q": "What is the WiFi password for the girls hostel second floor?",
        "type": "unanswerable",
        "lang": "en",
        "category": "hostel"
    }
]

async def run_evaluation():
    print("==================================================================")
    print("EASA DeskBot: Comprehensive Evaluation Benchmark (V2.2)")
    print("Factual Correctness, Multilingual (EN/TA/Tanglish), & Abstention")
    print("==================================================================")
    
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
    tamil_queries = sum(1 for item in BENCHMARK_DATASET if item.get("lang") == "ta")
    
    true_positives = 0
    factual_matches = 0
    tamil_matches = 0
    true_negatives = 0
    false_positives = 0

    print(f"\nEvaluating {len(BENCHMARK_DATASET)} queries ({total_answerable} answerable, {total_unanswerable} unanswerable, {tamil_queries} Tamil/Tanglish)...\n")

    for idx, item in enumerate(BENCHMARK_DATASET, 1):
        q = item["q"]
        expected_type = item["type"]
        lang = item.get("lang", "en")
        history = item.get("history", None)
        expected_facts = item.get("expected_facts", [])

        res = await pipeline.answer_query(q, language=lang, history=history)
        is_grounded = res.grounded

        if expected_type == "answerable":
            if is_grounded:
                true_positives += 1
                # Check factual correctness
                ans_text = res.answer.lower()
                has_fact = any(fact.lower() in ans_text for fact in expected_facts) if expected_facts else True
                if has_fact:
                    factual_matches += 1
                if lang == "ta":
                    tamil_matches += 1
                status_str = f"PASS (Grounded | Factually Accurate: {has_fact})"
            else:
                status_str = "FAIL (Under-retrieval)"
        else:
            if not is_grounded:
                true_negatives += 1
                status_str = "PASS (Strict Abstention)"
            else:
                false_positives += 1
                status_str = "FAIL (Hallucination risk on unverified fact)"

        print(f"[{idx:02d}] [{lang.upper()}] {q[:45]:<45} | {status_str}")

    grounded_recall = (true_positives / total_answerable) * 100 if total_answerable > 0 else 0
    factual_accuracy = (factual_matches / total_answerable) * 100 if total_answerable > 0 else 0
    abstention_precision = (true_negatives / (true_negatives + false_positives)) * 100 if (true_negatives + false_positives) > 0 else 0
    abstention_recall = (true_negatives / total_unanswerable) * 100 if total_unanswerable > 0 else 0
    tamil_accuracy = (tamil_matches / tamil_queries) * 100 if tamil_queries > 0 else 0

    print("\n------------------------------------------------------------------")
    print("V2.2 BENCHMARK EVALUATION METRICS:")
    print(f"Total Benchmark Queries       : {len(BENCHMARK_DATASET)}")
    print(f"Grounded Retrieval Recall     : {grounded_recall:.1f}%")
    print(f"Factual Answer Correctness    : {factual_accuracy:.1f}%")
    print(f"Strict Abstention Precision   : {abstention_precision:.1f}% (Zero-Hallucination on missing facts)")
    print(f"Strict Abstention Recall      : {abstention_recall:.1f}%")
    print(f"Tamil & Tanglish Retrieval Acc: {tamil_accuracy:.1f}%")
    print("------------------------------------------------------------------")
    print("STATUS: V2.2 EVALUATION BENCHMARK COMPLETED SUCCESSFULLY.")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
