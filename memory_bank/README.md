# scan2epub Memory Bank

This directory contains a comprehensive knowledge base about the scan2epub project, organized for easy reference and future development.

## What is scan2epub?

scan2epub is a Python tool that converts scanned or photographed PDF books into clean, reader-optimized EPUB files using Azure AI services. It was created by János Horváth-Varga (hvj78) as a hobby project to help his family read books on ONYX eBook readers.

## Memory Bank Structure

| File | Description | Key Information |
|------|-------------|-----------------|
| [INDEX.md](./INDEX.md) | Navigation hub and quick overview | Project summary, links to all sections |
| [README.md](./README.md) | Memory bank guide and quick reference | How to use this knowledge base |
| [01_project_overview.md](./01_project_overview.md) | Project purpose and features | Background, motivation, unique value proposition |
| [02_technical_architecture.md](./02_technical_architecture.md) | System design and components | Architecture diagrams, data flow, dependencies |
| [03_azure_configuration.md](./03_azure_configuration.md) | Azure setup and configuration | Required services, environment setup, troubleshooting |
| [04_usage_guide.md](./04_usage_guide.md) | How to use the tool | Installation, command-line options, examples |
| [05_code_structure.md](./05_code_structure.md) | Code organization and key functions | Module details, algorithms, processing flow |
| [06_limitations_issues.md](./06_limitations_issues.md) | Current constraints and known problems | Limitations, workarounds, troubleshooting |
| [07_roadmap.md](./07_roadmap.md) | Future development plans | Planned features, timeline, contribution opportunities |

## Project Structure

The scan2epub project now includes this comprehensive memory bank:

```
scan2epub/
├── .clineignore          # Cline-specific ignore file
├── .clinerules           # Cline-specific rules and memory bank configuration
├── .env                  # Environment variables (user created)
├── .env.template         # Template for environment configuration
├── .gitignore           # Git ignore rules
├── LICENSE              # MIT License
├── README.md            # Project documentation
├── requirements.txt     # Python dependencies
├── scan2epub.py         # Main entry point and orchestrator
├── pdf_ocr_processor.py # PDF OCR processing module
├── epub_builder.py      # EPUB construction module
├── docs/                # Documentation directory
│   └── azure-setup.md   # Azure setup documentation
├── memory_bank/         # Comprehensive project knowledge base
│   ├── INDEX.md         # Navigation hub
│   ├── README.md        # Memory bank guide
│   ├── 01_project_overview.md
│   ├── 02_technical_architecture.md
│   ├── 03_azure_configuration.md
│   ├── 04_usage_guide.md
│   ├── 05_code_structure.md
│   ├── 06_limitations_issues.md
│   └── 07_roadmap.md
└── personal/            # Personal/private files (gitignored)
```

## Quick Facts

- **Repository**: https://github.com/hvj78/scan2epub
- **License**: MIT License
- **Language**: Python 3.8+
- **Main Dependencies**: Azure AI services, ebooklib, BeautifulSoup4
- **Current Version**: v1.0 (Azure-dependent)
- **Next Major Goal**: Local AI model support (eliminate Azure dependency)

## Key Features

✅ **Two-stage processing**: OCR extraction + AI cleanup  
✅ **Flexible modes**: Full pipeline, OCR-only, or cleanup-only  
✅ **Hungarian optimization**: Specialized for Hungarian text  
✅ **Memory management**: Options for large file processing  
✅ **Debug support**: Detailed logging and troubleshooting  

## Major Limitations

❌ **Azure dependency**: Requires expensive cloud services  
❌ **PDF URL requirement**: Cannot process local files directly  
❌ **Single language focus**: Optimized primarily for Hungarian  
❌ **No image preservation**: Text-only processing  
❌ **Memory intensive**: Large EPUBs can cause issues  

## Development Priorities

1. **Local AI Support** (High Priority) - Eliminate Azure dependency
2. **Multi-language Support** (Medium Priority) - Expand beyond Hungarian
3. **Direct PDF Processing** (Medium Priority) - Handle local files
4. **GUI Interface** (Lower Priority) - User-friendly interface

## How to Use This Memory Bank

1. **Start with INDEX.md** for navigation and overview
2. **Check the roadmap** to understand future plans
3. **Review limitations** to understand current constraints
4. **Use technical architecture** for development understanding
5. **Reference usage guide** for practical implementation

## Last Updated

January 9, 2025

---

This memory bank was created to preserve comprehensive knowledge about the scan2epub project and facilitate future development and contributions.
