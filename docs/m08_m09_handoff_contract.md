# POLICY PILOT — M08 TO M09 HANDOFF CONTRACT & BOUNDARY SPECIFICATION

**Document Version:** 1.0.0  
**Status:** Authoritative & Frozen for M08 Integration Gate  
**Reference Commit:** `eb09a9d` (`feat(m08.7): complete employee policy catalog`)  

---

## 1. Executive Summary

This specification establishes the explicit boundary, security requirements, and data contract between:
- **Module M08:** Policy & Regulation Management System (Metadata, Versioning, Lifecycle, File Storage, Admin Management, Employee Catalog).
- **Module M09:** Policy Document Parser & Hybrid Ingestion Engine (Adaptive RAG, Parsing, OCR, Chunking, Embeddings, Vector/BM25 Indexing).

---

## 2. Explicit Ownership & Architectural Boundary

| Architectural Layer | Owned by Module M08 | Owned by Module M09 |
| :--- | :---: | :---: |
| Policy Core Metadata (`policy_code`, `title`, `category`, `policy_type`, `status`) | **YES** | NO |
| Regulatory Authority Catalog (`RBI`, `SEBI`, `NHB`, etc.) | **YES** | NO |
| Applicability Scoping (`institution`, `jurisdiction`, `loan_type`, `department`) | **YES** | NO |
| Version Lineage & Lifecycle State Machine (`DRAFT` → `PUBLISHED` → `ACTIVE` → `SUPERSEDED` → `ARCHIVED`) | **YES** | NO |
| Source Document Ingestion & Validation (MIME, Magic Bytes, Extension, 10MB limit) | **YES** | NO |
| Cryptographic Document Hashing (SHA-256) & Physical Storage Isolation | **YES** | NO |
| Controlled Document Access (Admin / Verified Employee RBAC) | **YES** | NO |
| Document Parsing & Structural Text Extraction | NO | **YES** |
| OCR Fallback for Scanned PDFs / Images | NO | **YES** |
| Semantic Clause & Section Chunking | NO | **YES** |
| Chunk-Level Metadata Attribution & Lineage Binding | NO | **YES** |
| Embedding Generation (Gemini / OpenAI / HuggingFace) | NO | **YES** |
| Vector Indexing (`pgvector` / HNSW) | NO | **YES** |
| Keyword / BM25 Inverted Indexing | NO | **YES** |
| Ingestion Pipeline Orchestration & Retry Tracking | NO | **YES** |
| RAG Retrieval & Compliance Evaluation Reasoning | NO | **YES (M10/M11)** |

### Strict M08 Invariants
Module M08 **MUST NEVER**:
1. Parse policy text content for RAG or chunk document text into snippets.
2. Generate embeddings or create `pgvector` / vector store records.
3. Call an LLM (Gemini, OpenAI, Anthropic, or local model) or perform compliance reasoning.
4. Perform hybrid search, BM25 indexing, or cross-encoder reranking.

---

## 3. M09 Ingestion Input Preconditions

Before Module M09 can accept an ingestion task, the target policy entity must satisfy all of the following preconditions:

1. **Active Lifecycle State:**  
   The policy `status` must strictly equal `PolicyStatus.ACTIVE`. Policies in `DRAFT`, `PUBLISHED`, `SUPERSEDED`, or `ARCHIVED` status are not eligible for ingestion.
2. **Current Version Binding:**  
   The policy must have a non-null `current_version_id` pointing to an existing `PolicyVersion` record.
3. **Valid File Binding:**  
   The bound `PolicyVersion` must have:
   - A non-empty cryptographic hash (`file_hash` SHA-256).
   - A positive file size (`file_size_bytes > 0`).
   - A valid stored path/URL (`file_url`).
4. **Physical Storage Verification:**  
   The source document file must physically reside in the isolated storage directory (`storage/policies/{policy_id}/{version_id}/`) and be verified via `PolicyFileService.get_policy_version_file`.
5. **Metadata Preservation:**  
   The M09 chunking engine must attach `policy_id`, `policy_version_id`, `version_number`, and all active `applicabilities` to every chunk vector for downstream authorization filtering.

---

## 4. Contract Schema (Backend Service)

The contract is implemented in Python via [`backend/app/services/m09_handoff_service.py`](file:///d:/POLICY%20PILOT%20RAG/backend/app/services/m09_handoff_service.py):

### 4.1 Policy Contract (`M09PolicyContract`)
```json
{
  "policy_id": "UUID",
  "policy_code": "POL-RETAIL-001",
  "title": "Retail Mortgage Underwriting Directive",
  "description": "Prudential loan-to-value norms for home loans",
  "category": "LENDING",
  "policy_type": "CREDIT_FRAMEWORK",
  "status": "ACTIVE",
  "institution": "HDFC-CORP",
  "jurisdiction": "NATIONAL",
  "regulatory_authority": {
    "id": "UUID",
    "name": "Reserve Bank of India",
    "short_name": "RBI",
    "jurisdiction": "IN",
    "website_url": "https://www.rbi.org.in"
  }
}
```

### 4.2 Policy Version Contract (`M09PolicyVersionContract`)
```json
{
  "policy_version_id": "UUID",
  "policy_id": "UUID",
  "version_number": "1",
  "effective_from": "2026-01-01T00:00:00Z",
  "effective_to": null,
  "file_url": "/api/employee/policies/{policy_id}/versions/{version_id}/file",
  "file_hash": "a1b2c3d4e5...",
  "file_size_bytes": 1048576,
  "page_count": 24,
  "changelog": "Initial baseline approved by committee",
  "created_at": "2026-01-01T00:00:00Z"
}
```

### 4.3 Applicability Contract (`M09PolicyApplicabilityContract`)
```json
[
  {
    "id": "UUID",
    "institution": "HDFC-CORP",
    "jurisdiction": "NATIONAL",
    "loan_type": "HOME_LOAN",
    "department": "UNDERWRITING",
    "created_at": "2026-01-01T00:00:00Z"
  }
]
```

### 4.4 Top-Level Handoff Payload (`M09HandoffPayload`)
```json
{
  "policy": { ... },
  "version": { ... },
  "applicabilities": [ ... ],
  "is_source_document_verified": true,
  "source_filename": "mortgage_guideline_v1.pdf"
}
```

---

## 5. Security, Immutability & File Safety Rules

1. **Version Immutability:**  
   Once a `PolicyVersion` is bound to a document (`file_hash`, `file_size_bytes`, `version_number`), those fields are frozen and cannot be updated in-place.
2. **Zero Storage Path Leakage:**  
   External APIs (Admin and Employee) must never expose local file paths (e.g. `D:\POLICY PILOT RAG\backend\storage\...`). Only internal service calls (e.g. `M09HandoffService.get_policy_version_source_file`) have access to resolved paths.
3. **Controlled Stream Streaming:**  
   Clients receive files via authenticated HTTP streaming (`FileResponse`) with proper MIME headers (`application/pdf`) and content disposition.
4. **Historical Version Availability:**  
   When a policy is superseded by version 2, version 1 remains accessible to authorized roles through `/api/employee/policies/{id}/history` and `/api/admin/policies/{id}/history`.
5. **Archival Invisibility:**  
   When a policy enters `ARCHIVED` status, it immediately disappears from the Employee Policy Catalog (`/api/employee/policies`) and detail lookups return `404 Not Found`.
