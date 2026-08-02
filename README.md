# Ledger API

🔗 **Live demo:** [taskapi-fronend.vercel.app](https://taskapi-fronend.vercel.app)
🎨 **Frontend repo:** [taskapi-frontend](https://github.com/HillolPias/taskapi-fronend)

The backend for **Ledger** — a full-stack task/project manager built around a real AI agent, not a chatbot wrapper.

A LangGraph-orchestrated ReAct agent reasons, selects from 17 tools, and observes results in a loop — creating/updating tasks and projects, and answering questions grounded in live database retrieval (RAG via ChromaDB) rather than guessing. Responses stream token-by-token via `astream_events`, and every run is traced end-to-end in LangSmith.

**Stack:** FastAPI · async SQLAlchemy 2.0 · PostgreSQL (Neon) · Alembic migrations · LangChain/LangGraph · OpenAI (`gpt-4o-mini`) · ChromaDB
**Deployed:** Render

## License

This project is licensed under the [MIT License](LICENSE).
