# scan2epub Memory Bank

This memory bank contains comprehensive information about the scan2epub project, following the .clinerules specification for Cline's memory management.

## Core Memory Files (Required by .clinerules)

These files form the foundation of the memory bank and build upon each other:

- **[projectbrief.md](./projectbrief.md)** - Foundation document defining core requirements and goals
- **[productContext.md](./productContext.md)** - Why this project exists and how it should work
- **[systemPatterns.md](./systemPatterns.md)** - Architecture, design patterns, and technical decisions
- **[techContext.md](./techContext.md)** - Technologies, setup, constraints, and tools
- **[activeContext.md](./activeContext.md)** - Current work focus, recent changes, and next steps
- **[progress.md](./progress.md)** - What works, what's left to build, and project evolution

## Additional Context Files

These files provide detailed information about specific aspects:

- **[01_project_overview.md](./01_project_overview.md)** - Legacy: Project purpose and background
- **[02_technical_architecture.md](./02_technical_architecture.md)** - Legacy: System design details
- **[03_azure_configuration.md](./03_azure_configuration.md)** - Azure setup and troubleshooting guide
- **[04_usage_guide.md](./04_usage_guide.md)** - Installation and usage instructions
- **[05_code_structure.md](./05_code_structure.md)** - Code organization and implementation details
- **[06_limitations_issues.md](./06_limitations_issues.md)** - Current constraints and known problems
- **[07_roadmap.md](./07_roadmap.md)** - Future development plans and contribution opportunities

## Project Summary

**scan2epub** is a Python-based tool created by János Horváth-Varga (hvj78) that:
- Converts scanned/photographed PDFs to EPUB format
- Uses Azure AI Content Understanding for OCR
- Uses Azure GPT-4 for text cleanup and optimization
- Supports Hungarian and other languages
- Offers flexible processing modes (full pipeline, OCR-only, cleanup-only)

## Key Information

- **Repository**: https://github.com/hvj78/scan2epub
- **License**: MIT License
- **Primary Language**: Python 3.8+
- **Main Dependencies**: Azure AI services, ebooklib, BeautifulSoup4
- **Created**: As a hobby project for family use with ONYX eBook readers

## Memory Bank Structure

According to .clinerules, the memory bank follows this hierarchy:

```
projectbrief.md (foundation)
    ├── productContext.md
    ├── systemPatterns.md
    └── techContext.md
            └── activeContext.md
                    └── progress.md
```

## How to Use This Memory Bank

1. **For Cline**: Start by reading all core files in order to understand the complete project context
2. **For Developers**: Use additional context files for specific implementation details
3. **For Contributors**: Check roadmap.md and activeContext.md for current priorities
4. **For Users**: Refer to usage_guide.md and limitations_issues.md

## Last Updated

January 9, 2025 - Restructured to comply with .clinerules specification
