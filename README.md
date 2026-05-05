# 🤖 AI ChatOps Assistant

**Internal AI Chatbot for Company Knowledge Management**

A secure, role-based conversational AI assistant that provides instant access to company documentation, policies, and procedures through natural language queries.

---

## ✨ Features

### Core Capabilities
- 🔍 **Retrieval-Augmented Generation (RAG)** - Accurate answers from your documents
- 🔐 **Role-Based Access Control (RBAC)** - Granular document access by user role
- 💬 **Conversational Interface** - Natural multi-turn dialogue with context memory
- 📚 **Source Citations** - Every answer includes document references
- 🛠️ **Tool Integration** - Extensible with custom tools (PTO balance, etc.)
- 📊 **Analytics Dashboard** - Query patterns, knowledge gaps, user activity
- 🔄 **Auto Re-indexing** - Monitors document changes and rebuilds database
- 🐳 **Docker Support** - One-command deployment with docker-compose

### Security & Privacy
- ✅ User authentication with bcrypt password hashing
- ✅ Role-based document filtering
- ✅ Sensitive information redaction in logs
- ✅ Local LLM processing (no data sent externally)
- ✅ Complete audit trail of all queries

### Document Support
- 📄 PDF files
- 📝 Word documents (.docx)
- 📰 Text files (.txt)
- 📋 Markdown files (.md)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11
- 8GB RAM (16GB recommended)
- 10GB disk space

### Installation (5 minutes)

```bash
# 1. Clone and setup
cd chat-assistant
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download AI model
python download_model.py

# 4. Add your documents
# Place files in knowledge_base/[role]/ folders
# Supported roles: general, hr, finance, it_support, engineering

# 5. Build knowledge base
python ingest.py

# 6. Start application
streamlit run app.py
```

**Access at**: http://localhost:8501

**Default credentials**:
- Username: `admin` / Password: `admin123`

---

## 📁 Project Structure

```
chat-assistant/
├── app.py                      # Main chat interface
├── query.py                    # RAG & LLM logic
├── ingest.py                   # Document indexing
├── analytics_enhanced.py       # Analytics dashboard
├── auto_reindex.py            # Auto document monitoring
├── load_test.py               # Performance testing
├── config.yaml                # User management
├── requirements.txt           # Dependencies
│
├── knowledge_base/            # Your documents (by role)
│   ├── general/              # Accessible to all
│   ├── hr/                   # HR-only documents
│   ├── finance/              # Finance-only documents
│   ├── it_support/           # IT Support documents
│   └── engineering/          # Engineering documents
│
├── db/                        # Vector database
└── Dockerfile                 # Docker configuration
```

---

## 🎯 Usage Examples

### For End Users

**Ask questions naturally:**
- "What is the PTO policy?"
- "How do I troubleshoot the VPN?"
- "What is the monthly finance approval limit?"
- "How do I deploy code to production?"

**Get instant answers with sources:**
```
Answer: The PTO policy allows all employees to take up to 20 days 
of paid time off each year...

📚 Sources:
- general/company_policy.txt
- general/leaves.txt
```

### For Administrators

**Add new documents:**
```bash
# 1. Drop files in appropriate folder
cp new_policy.pdf knowledge_base/hr/

# 2. Re-index
python ingest.py

# 3. Documents are now searchable!
```

**Monitor with auto re-indexing:**
```bash
python auto_reindex.py --watch
# Automatically rebuilds database when files change
```

**View analytics:**
```bash
streamlit run analytics_enhanced.py --server.port 8502
# Open http://localhost:8502
```

---

## 🔐 Security & Access Control

### User Roles

| Role | Access |
|------|--------|
| **admin** | Full access to all documents |
| **hr** | HR documents + general |
| **finance** | Finance documents + general |
| **it_support** | IT documents + general |
| **engineering** | Engineering documents + general |
| **general** | General documents only |

### Adding Users

Edit `config.yaml`:

```yaml
credentials:
  usernames:
    john:
      email: john@company.com
      name: John Doe
      password: $2b$12$...  # bcrypt hash
      role: hr
```

Generate password hash:
```python
import bcrypt
print(bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode())
```

---

## 📊 Analytics & Monitoring

### Built-in Dashboards

1. **Overview** - Key metrics, query timeline, user distribution
2. **Knowledge Gaps** - Unanswered queries, content recommendations
3. **User Activity** - Engagement heatmap, role distribution
4. **Query Patterns** - Top queries, keyword analysis
5. **Raw Data** - Filterable query logs with CSV export

### Performance Testing

```bash
# Quick test
python load_test.py --queries 10

# Load test with 100 concurrent queries
python load_test.py --queries 100 --concurrent 10
```

---

## 🐳 Docker Deployment

### Quick Deploy

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Services

- **Main App**: http://localhost:8501
- **Analytics**: http://localhost:8502

### Update Documents

```bash
# Add documents to knowledge_base/
cp new_doc.pdf knowledge_base/hr/

# Rebuild inside container
docker-compose exec chatops-app python ingest.py

# Restart
docker-compose restart chatops-app
```

---

## 🛠️ Configuration

### LLM Settings (`query.py`)

```python
config={
    "max_new_tokens": 256,      # Response length
    "temperature": 0.01,        # Creativity (0-1)
    "repetition_penalty": 1.15, # Avoid repetition
}
```

### Retrieval Settings

```python
search_kwargs = {"k": 3}  # Number of documents to retrieve
```

### Embedding Model

Currently using: **BAAI/bge-large-en-v1.5**
- High accuracy semantic search
- Optimized for English
- CPU-friendly

---

## 📈 Performance

### Benchmarks (Local CPU)

| Metric | Value |
|--------|-------|
| **Avg Response Time** | 2-4 seconds |
| **Throughput** | 0.5-1 queries/sec (sequential) |
| **Concurrent Capacity** | 5-10 simultaneous users |
| **Database Size** | ~10MB per 1000 documents |
| **RAM Usage** | 4-6GB (with LLM loaded) |

### Optimization Tips

1. **Reduce `max_new_tokens`** - Faster responses
2. **Increase `threads`** - Better CPU utilization
3. **Use GPU** - 10x faster inference
4. **Cache embeddings** - Faster retrieval
5. **Batch re-indexing** - Efficient updates

---

## 🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Model not found | Run `python download_model.py` |
| No documents found | Check `knowledge_base/` and run `python ingest.py` |
| Chroma DB error | Delete `db/` and run `python ingest.py` |
| Out of memory | Reduce `max_new_tokens` or use smaller model |
| Slow responses | Check CPU usage, reduce concurrent users |

### Debug Commands

```bash
# Test query system
python query.py

# Test RBAC
python test_rbac.py

# Check database
python debug_retrieval.py

# View logs
tail -f chat_log.jsonl
```

---

## 📚 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide
- **[API.md](API.md)** - API reference (if applicable)
- **config.yaml** - User management reference

---

## 🤝 Contributing

### Adding New Features

1. **New Tools** - Add to `query.py` `BasicAgent` class
2. **New Roles** - Update `config.yaml` and folder structure
3. **New File Types** - Update `LOADER_MAP` in `ingest.py`

### Code Style

- Python 3.11+
- Black formatter
- Type hints recommended
- Docstrings for functions

---

## 📝 License

Proprietary - Internal Use Only
© 2025 Your Company

---

## 🎯 Roadmap

### Phase 1 ✅ (Complete)
- [x] RAG pipeline
- [x] RBAC
- [x] Chat interface
- [x] Analytics
- [x] Docker support

### Phase 2 🚧 (Future)
- [ ] SSO/OAuth integration
- [ ] Multi-language support
- [ ] Advanced analytics (ML insights)
- [ ] Mobile app
- [ ] Voice interface

### Phase 3 💡 (Planned)
- [ ] Graph RAG
- [ ] Fine-tuned models
- [ ] Real-time collaboration
- [ ] API endpoints
- [ ] Slack/Teams integration

---

## 📞 Support

For technical support:
- **Internal**: IT Support team
- **Documentation**: See `DEPLOYMENT.md`
- **Issues**: Check troubleshooting section

---

## ⭐ Acknowledgments

Built with:
- [LangChain](https://python.langchain.com/) - RAG framework
- [Streamlit](https://streamlit.io/) - Web interface
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Zephyr-7B](https://huggingface.co/HuggingFaceH4/zephyr-7b-beta) - Language model
- [BGE Embeddings](https://huggingface.co/BAAI/bge-large-en-v1.5) - Semantic search

---

**🎉 Ready to transform your company's knowledge management!**

*Built with ❤️ for efficient, secure, and intelligent information access*