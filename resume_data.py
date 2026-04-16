resume = {
    "name": "Aditya Bisht",
    "contact": {
        "phone": "+91 7982759592",
        "email": "aaditya85677@gmail.com",
        "location": "New Delhi, India",
        "linkedin": "your-linkedin-url",
        "github": "your-github-url"
    },
    "summary": "AI/ML Engineer skilled in LangChain, LangGraph, RAG Systems, and agentic AI. Built and benchmarked 7 RAG strategies across 3,500 evaluation pairs. Fine-tuned Qwen2.5-1.5B to 85.3% accuracy at $0.0002/query.",
    
    "skills": {
        "expert": ["Python", "LangChain", "LangGraph", "RAG Systems", "LLMs", 
                   "Agentic AI", "FastAPI", "Pandas", "NumPy"],
        "proficient": ["Fine-tuning", "LoRA", "PyTorch", "TensorFlow", "FAISS", 
                       "Pinecone", "Vector Databases", "JavaScript", "TypeScript",
                       "Node.js", "Express.js", "React.js", "Streamlit", "REST APIs",
                       "Machine Learning", "Deep Learning", "Neural Networks", 
                       "Git/GitHub", "DSA", "OOP", "DBMS"],
        "familiar": ["C++", "Java", "n8n", "MCP", "MLOps", "Docker", 
                     "HTML5/CSS", "Computer Networks"]
    },
    
    "projects": [
        {
            "name": "RAG Systems Eval Suite",
            "tech": ["Python", "FAISS", "BM25", "LangChain", "Groq API", 
                     "Cerebras", "Streamlit", "SQLite", "Pydantic"],
            "bullets": [
                "Benchmarked 7 RAG retrieval strategies across 50 questions × 10 automated metrics, with Advanced RAG achieving 0.881 faithfulness and 0.816 hallucination control vs 0.760 and 0.221 for Base LLM",
                "Engineered hybrid retrieval pipeline combining FAISS semantic search + BM25 keyword search with Reciprocal Rank Fusion and cross-encoder reranking, lifting faithfulness from 0.738 → 0.816 → 0.881",
                "Built dual-provider LLM-as-judge pipeline evaluating 3,500 answer-metric pairs with checkpoint/resume on API quota exhaustion without data loss",
                "Developed Streamlit analytics dashboard visualising per-system scores across all 10 metrics with radar and bar charts"
            ]
        },
        {
            "name": "CodeSage",
            "tech": ["Python", "LangChain", "FAISS", "HuggingFace PEFT", 
                     "LoRA", "Streamlit", "Groq API"],
            "bullets": [
                "Fine-tuned Qwen2.5-1.5B with LoRA achieving 85.3% accuracy, 0% hallucination rate, and $0.0002/query cost — outperforming Baseline LLM (43.2% hallucination) on all quality metrics",
                "Built RAG pipeline with FAISS + all-MiniLM-L6-v2 embeddings achieving 81.6% answer accuracy and 0.87 groundedness, cutting hallucination rate from 43.2% → 9.8%",
                "Automated evaluation of 3 systems × 50 Q&A pairs × 5 metrics with persistent caching — zero manual scoring",
                "Developed Streamlit dashboard with side-by-side comparison, winner badges, hallucination flags across all 3 systems"
            ]
        },
        {
            "name": "Autonomous MLOps Incident Response Agent",
            "tech": ["Python", "FastAPI", "XGBoost", "LangGraph", "Evidently AI", 
                     "MLflow", "Prometheus", "Grafana", "Docker"],
            "bullets": [
                "Built autonomous MLOps agent for UPI fraud detection using LangGraph + XGBoost, reducing model degradation response time from days to <60 seconds with zero human intervention",
                "Engineered real-time drift monitoring pipeline detecting feature distribution shifts across 8 input features every 5 minutes, triggering automated retrain/rollback at 0.95 confidence",
                "Designed 6-service Dockerized stack with hot-reload model swapping, achieving ROC-AUC of 0.99 post-retrain on 10,000-row synthetic UPI dataset",
                "Implemented MLflow experiment tracking with model registry promotion logic and 6-panel Grafana observability dashboard"
            ]
        }
    ],
    
    "education": {
        "college": "Maharaja Agrasen Institute of Technology, GGSIPU",
        "degree": "Bachelor of Information Technology",
        "cgpa": "8.0",
        "year": "2023-2027"
    },
    
    "certifications": [
        "Oracle Generative AI Professional",
        "Oracle AI Vector Search Professional"
    ]
}