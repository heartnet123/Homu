# Phase 3: Hybrid Search & Reranking

## Overview
Phase 3 improves retrieval quality by combining BM25 keyword search, vector semantic search, and cross-encoder reranking.

## Features

### 1. BM25 Keyword Search
- Lexical matching using BM25Okapi algorithm
- Thai-aware tokenization (handles Thai characters, numbers, English words)
- Persistent index storage in `data/bm25_indices/`
- Per-collection indices

### 2. Vector Search (Existing)
- Semantic similarity using `airesearch/WangchanX-Legal-ThaiCCL-Retriever`
- ChromaDB for vector storage

### 3. Hybrid Search (Recommended)
- Combines BM25 + Vector using Reciprocal Rank Fusion (RRF)
- RRF formula: `score = 1 / (k + rank)` where k=60
- Results from both methods are fused and re-ranked

### 4. Cross-Encoder Reranker
- Multilingual model: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`
- Reranks top-k candidates for better relevance
- Final score: `0.7 * reranker_score + 0.3 * hybrid_score`

### 5. Confidence-Based Multi-Collection Search
- Confidence threshold (default 0.5) determines result quality
- If confidence is low in selected collection, system automatically expands to search all collections
- Helps find relevant documents across different legal domains

## API Changes

### Chat Request
```json
{
  "messages": [...],
  "collectionId": "optional-collection-id",
  "searchStrategy": "hybrid",  // "bm25" | "vector" | "hybrid"
  "confidenceThreshold": 0.5   // 0.0 to 1.0
}
```

### Search Strategies
- `bm25`: Keyword-only search (fast, exact matches)
- `vector`: Semantic-only search (context-aware)
- `hybrid`: BM25 + Vector + Reranker (best quality, default)

## UI Changes

### Settings Button
- Located in the header (gear icon)
- Opens settings modal with:
  - Search strategy selector (3 options with Thai descriptions)
  - Confidence threshold slider (0.0 - 1.0)

### Search Strategy Descriptions
- **BM25**: ค้นหาด้วยคำสำคัญ (keywords) - Best for finding specific sections/articles
- **Vector**: ค้นหาด้วยความหมาย (semantic) - Best for general questions
- **Hybrid**: รวม BM25 + Vector + Cross-encoder Reranker - Recommended

## Files Changed

### Backend
- `requirements.txt` - Added `rank-bm25`, `sentencepiece`, `scikit-learn`
- `hybrid_search.py` - New module with BM25, hybrid search, reranking
- `retriever.py` - Integrated BM25 indexing with document add/delete
- `graph.py` - Added search strategy parameter and confidence logic
- `main.py` - API endpoints accept search strategy and confidence threshold

### Frontend
- `page.tsx` - Added settings modal, search strategy selector, confidence slider

## Installation

```bash
cd backend
pip install -r requirements.txt
```

## Testing

1. Upload documents to a collection
2. Click the settings (gear) icon in the header
3. Try different search strategies:
   - BM25: Good for "มาตรา 12" or specific keywords
   - Vector: Good for "การเลิกจ้างงานมีสิทธิอะไรบ้าง"
   - Hybrid: Best overall quality
4. Adjust confidence threshold (lower = more likely to search all collections)

## Architecture

```
User Query
    ↓
[Search Strategy Selector]
    ↓
┌─────────────────┐  ┌─────────────────┐
│   BM25 Index    │  │  Vector Search  │
│  (keyword)      │  │  (semantic)     │
└─────────────────┘  └─────────────────┘
         ↓                    ↓
    ┌─────────────────────────────┐
    │   Reciprocal Rank Fusion    │
    │     (RRF scoring)           │
    └─────────────────────────────┘
                   ↓
    ┌─────────────────────────────┐
    │   Cross-Encoder Reranker  │
    │  (mmarco-mMiniLMv2-L12)   │
    └─────────────────────────────┘
                   ↓
    [Confidence Check] → [Expand to all collections if low]
                   ↓
         Top-k Results to LLM
```

## Performance Notes

- BM25: Fast, low memory overhead
- Vector: Moderate speed, GPU optional
- Hybrid: Slightly slower due to dual search + reranking
- Cross-encoder: ~50-100ms per query on CPU

## Fallback Behavior

If hybrid search fails (e.g., model not loaded), system automatically falls back to vector-only search.
