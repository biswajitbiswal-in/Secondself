# Deployment Preparation TODO

## Phase 1: Code Fixes ✅
- [x] 1. Add `beautifulsoup4` to `requirements.txt`
- [x] 2. Fix `capture.py` frontmatter import hack
- [x] 3. Create `.streamlit/config.toml`
- [x] 4. Create `runtime.txt`
- [x] 5. Update `.gitignore` for deployment
- [x] 6. Update `README.md` with deployment section
- [x] 7. Add graceful API key startup check in `app.py`

## Phase 2: Build & Test
- [ ] 8. Run pipeline locally: `python pipeline.py process`
- [ ] 9. Build graph: `python build_graph.py`
- [ ] 10. Force-add embeddings.pkl for deploy: `git add -f data/embeddings.pkl`
- [ ] 11. Test locally: `streamlit run app.py`

## Phase 3: Commit & Deploy
- [ ] 12. Commit all changes: `git add -A && git commit -m "Prepare for Streamlit Cloud deploy"`
- [ ] 13. Push to GitHub: `git push -u origin main`
- [ ] 14. Configure on share.streamlit.io
- [ ] 15. Add GROQ_API_KEY secret in Streamlit dashboard
- [ ] 16. Verify live URL

