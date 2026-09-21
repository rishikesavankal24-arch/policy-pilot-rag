# PolicyPilot Architecture

## Overview
PolicyPilot is an AI-powered banking policy and regulatory compliance platform.

## Technology Stack
- **Frontend**: Next.js, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python, uv
- **Database**: PostgreSQL with pgvector extension (Docker Compose)
- **AI Engine**: Adaptive RAG, Hybrid Retrieval, Reranking
- **LLM**: Configurable (Gemini, OpenAI, etc.)

## Project Modules Development Plan
The project is strictly developed in 20 sequential modules.

1. **Project Foundation & Architecture** (Current)
2. **Authentication & Onboarding**
3. **Users, Roles & RBAC**
4. **Customer Portal**
5. **Employee Portal**
6. **Loan Application Workflow**
7. **Document Management & Verification**
8. **Policy & Regulation Management**
9. **RAG Knowledge Ingestion Pipeline**
10. **Adaptive RAG Compliance Engine**
11. **Compliance Review & Evidence Workspace**
12. **Decision Workflow**
13. **Notification & Communication System**
14. **Audit Trail & Policy Versioning**
15. **Multilingual & Voice Layer**
16. **Policy Intelligence**
17. **Compliance Passport & Consent**
18. **Universal Compliance API**
19. **Reports & Analytics**
20. **Security, Evaluation, Testing & Production Deployment**

## Environment Variables
The system relies on environment-specific configurations. The primary variables include `DATABASE_URL`, `BACKEND_URL`, and `FRONTEND_URL`. See `.env.example` for details.
