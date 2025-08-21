# Active Context: scan2epub

## Current Work Focus

### Memory Bank Restructuring (January 11, 2025) - COMPLETED ✅
- Migrated from numbered documentation files to .clinerules-compliant structure
- Created core memory bank files: projectbrief.md, productContext.md, systemPatterns.md, techContext.md
- Moved .clinerules and .clineignore files from docs/ to project root
- Established proper memory bank hierarchy and dependencies
- Removed unnecessary legacy files: 01-07 numbered files, README.md, INDEX.md, 05_code_structure.md
- Retained valuable context files: 03_azure_configuration.md, 04_usage_guide.md

### Project Status
- Version: 0.1.0 (per pyproject.toml; functional with Azure dependency)
- State: Production-ready for Hungarian text processing for limited use
- Primary Use: Author's family actively using for book conversion
- Next Priority: Local AI model support to eliminate Azure costs

## Recent Changes

### File Structure Updates
1. Cline Configuration Files Moved:
   - `.clinerules` moved from `docs/` to root
   - `.clineignore` moved from `docs/` to root
   - Updated all documentation to reflect new structure

2. Memory Bank Created:
   - Comprehensive documentation following .clinerules specification
   - Core files establishing project foundation
   - Additional context files for detailed information

### Documentation Improvements
- Created structured knowledge base for future development
- Documented all current limitations and workarounds
- Established clear roadmap for community contributions

## Next Steps

### Immediate Tasks
1. Validate Memory Bank Structure: ✅ COMPLETED
   - Ensure all core files follow .clinerules guidelines ✅
   - Create progress.md to track project evolution ✅
   - Remove old numbered documentation files ✅

2. Test Current Implementation:
   - Verify Azure services are properly configured (use `scan2epub azure-test`)
   - Process a sample Hungarian book via new CLI:
     - `scan2epub ocr <input.pdf> <raw.epub>`
     - `scan2epub clean <raw.epub> <final.epub> --save-interim`
     - or `scan2epub pipeline <input.pdf> <final.epub> --save-interim`
   - Document any new issues discovered

### Short-term Goals
1. Local OCR Research:
   - Investigate Tesseract integration
   - Test PaddleOCR for Hungarian support
   - Create proof-of-concept for local processing

2. Memory Optimization:
   - Profile memory usage during large book processing
   - Implement streaming where possible
   - Optimize chunk size calculations

3. Azure Blob UX improvements:
   - Better error messages for connection string issues (AccountKey padding, length hints)
   - Auto-create container if missing (already implemented)
   - Optional automatic cleanup toggled via INI (Cleanup section)

## Active Decisions and Considerations

### Architecture Decisions
1. Keep Azure as Primary: Until local alternatives prove viable
2. Maintain Backward Compatibility: Don't break existing workflows
3. Prioritize Hungarian: Continue optimization for primary use case

### Technical Considerations
1. Memory Management:
   - Current --save-interim flag is a workaround, not a solution
   - Need proper streaming implementation
   - Consider chunked EPUB reading/writing

2. Error Handling:
   - Current graceful degradation works but could be smarter
   - Need better error messages for common issues
   - Consider recovery mechanisms for partial failures

3. Input Handling:
   - Local PDF paths now supported via Azure Blob upload → SAS URL bridge
   - Ensure `AZURE_STORAGE_CONNECTION_STRING` present; provide actionable diagnostics

## Important Patterns and Preferences

### Code Style
- Type hints for all function signatures
- Descriptive variable names over comments
- Early validation and fail-fast approach
- Comprehensive error messages for users

### Documentation Style
- Clear section headers with purpose
- Code examples where helpful
- Rationale for decisions documented
- User-focused explanations

### Development Workflow
1. Test changes with small files first
2. Use --debug flag during development
3. Monitor Azure costs during testing
4. Validate output in multiple EPUB readers

## Learnings and Project Insights

### What Works Well
1. Two-stage pipeline: Clean separation of concerns
2. Hungarian optimization: Excellent results for target language
3. Azure integration: Reliable when properly configured
4. Progress indication: Users appreciate feedback

### Pain Points
1. PDF URL requirement: Major friction for users
2. Azure costs: Expensive for large books
3. Memory usage: Problematic for book collections
4. Setup complexity: Azure configuration is challenging

### User Feedback
- Family members successfully using the tool
- Request for batch processing capabilities
- Desire for cost-free local processing
- Need for better error messages

### Technical Insights
1. Chunking is critical: Text must respect paragraph boundaries
2. Hungarian hyphenation: More complex than initially thought
3. EPUB structure: Varies significantly between sources
4. API rate limits: Real constraint for large books

## Current Blockers

### Technical Blockers
1. Azure Dependency: Prevents wider adoption due to cost
2. URL Requirement: Adds friction to user workflow
3. Memory Limitations: Can't process very large books reliably

### Resource Blockers
1. Development Time: Hobby project with limited time
2. Testing Resources: Need diverse PDF samples
3. Azure Costs: Expensive to test extensively

## Context for Next Session

When returning to this project:
1. Run `scan2epub azure-test` to validate environment (.env + INI + storage + CU + OpenAI)
2. Test end-to-end with a Hungarian PDF using the pipeline subcommand
3. Capture interim artifacts via `--debug` and `--save-interim` for analysis
4. Triage any storage/SAS issues and refine diagnostics
5. Update progress.md with findings and adjust roadmap

Remember: The primary goal is helping the family read books on their ONYX readers. All decisions should support this goal while making the tool useful for others.

---

## Automated Tests and Fail-fast Translation Guardrails (August 21, 2025) - COMPLETED ✅

Scope:
- Added unit tests to validate the new Translation stage, preflight behavior, and no-op guard.
- Ensured AppConfig resolves Azure OpenAI deployment from AZURE_OPENAI_DEPLOYMENT_NAME.

Key changes:
- Config:
  - src/scan2epub/config.py: deployment resolved via AZURE_OPENAI_DEPLOYMENT_NAME.
- Tests (pytest added to requirements.txt):
  - tests/test_openai_env_resolution.py — verifies env var name compatibility.
  - tests/test_translator_preflight.py — verifies AzureTranslator.preflight_check does exactly one POST, handles 404 and malformed response, and sets Region header when provided.
  - tests/test_epub_translation_noop_guard.py — verifies no-op translation raises TranslationError by default with translate_noop status event, allow_noop override, and min_changed_ratio enforcement.
  - tests/test_pipeline_translate_preflight_abort.py — verifies pipeline.run_translate hard-stops on preflight failure; PreflightChecker emits preflight_start and translator_failed to status JSONL on failure.
- Tooling:
  - requirements.txt: added pytest>=7.0.0.
  - tests/conftest.py: ensures src/ is on sys.path.

How to run:
- pip install -r requirements.txt
- pytest -q

Notes:
- No external network is used in unit tests; Translator and preflight behavior are mocked/stubbed.
- Tests build tiny synthetic EPUBs with ebooklib and exercise the end-to-end translation write path when allowed by guardrails.
