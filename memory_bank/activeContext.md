# Active Context: scan2epub

## Current Work Focus

### Memory Bank Restructuring (January 9, 2025)
- Migrated from numbered documentation files to .clinerules-compliant structure
- Created core memory bank files: projectbrief.md, productContext.md, systemPatterns.md, techContext.md
- Moved .clinerules and .clineignore files from docs/ to project root
- Established proper memory bank hierarchy and dependencies

### Project Status
- **Version**: 1.0 (Functional with Azure dependency)
- **State**: Production-ready for Hungarian text processing
- **Primary Use**: Author's family actively using for book conversion
- **Next Priority**: Local AI model support to eliminate Azure costs

## Recent Changes

### File Structure Updates
1. **Cline Configuration Files Moved**:
   - `.clinerules` moved from `docs/` to root
   - `.clineignore` moved from `docs/` to root
   - Updated all documentation to reflect new structure

2. **Memory Bank Created**:
   - Comprehensive documentation following .clinerules specification
   - Core files establishing project foundation
   - Additional context files for detailed information

### Documentation Improvements
- Created structured knowledge base for future development
- Documented all current limitations and workarounds
- Established clear roadmap for community contributions

## Next Steps

### Immediate Tasks
1. **Validate Memory Bank Structure**:
   - Ensure all core files follow .clinerules guidelines
   - Create progress.md to track project evolution
   - Remove old numbered documentation files

2. **Test Current Implementation**:
   - Verify Azure services are properly configured
   - Process a sample Hungarian book
   - Document any new issues discovered

### Short-term Goals
1. **Local OCR Research**:
   - Investigate Tesseract integration
   - Test PaddleOCR for Hungarian support
   - Create proof-of-concept for local processing

2. **Memory Optimization**:
   - Profile memory usage during large book processing
   - Implement streaming where possible
   - Optimize chunk size calculations

## Active Decisions and Considerations

### Architecture Decisions
1. **Keep Azure as Primary**: Until local alternatives prove viable
2. **Maintain Backward Compatibility**: Don't break existing workflows
3. **Prioritize Hungarian**: Continue optimization for primary use case

### Technical Considerations
1. **Memory Management**:
   - Current --save-interim flag is a workaround, not a solution
   - Need proper streaming implementation
   - Consider chunked EPUB reading/writing

2. **Error Handling**:
   - Current graceful degradation works but could be smarter
   - Need better error messages for common issues
   - Consider recovery mechanisms for partial failures

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
1. **Two-stage pipeline**: Clean separation of concerns
2. **Hungarian optimization**: Excellent results for target language
3. **Azure integration**: Reliable when properly configured
4. **Progress indication**: Users appreciate feedback

### Pain Points
1. **PDF URL requirement**: Major friction for users
2. **Azure costs**: Expensive for large books
3. **Memory usage**: Problematic for book collections
4. **Setup complexity**: Azure configuration is challenging

### User Feedback
- Family members successfully using the tool
- Request for batch processing capabilities
- Desire for cost-free local processing
- Need for better error messages

### Technical Insights
1. **Chunking is critical**: Text must respect paragraph boundaries
2. **Hungarian hyphenation**: More complex than initially thought
3. **EPUB structure**: Varies significantly between sources
4. **API rate limits**: Real constraint for large books

## Current Blockers

### Technical Blockers
1. **Azure Dependency**: Prevents wider adoption due to cost
2. **URL Requirement**: Adds friction to user workflow
3. **Memory Limitations**: Can't process very large books reliably

### Resource Blockers
1. **Development Time**: Hobby project with limited time
2. **Testing Resources**: Need diverse PDF samples
3. **Azure Costs**: Expensive to test extensively

## Context for Next Session

When returning to this project:
1. Check if Azure services are still configured properly
2. Review any new issues reported on GitHub
3. Consider starting with local OCR proof-of-concept
4. Test with a Hungarian book to ensure quality maintained
5. Update progress.md with any new developments

Remember: The primary goal is helping the family read books on their ONYX readers. All decisions should support this goal while making the tool useful for others.
