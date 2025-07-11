# Local PDF File Support

This document describes the new local PDF file support feature that allows scan2epub to process PDF files directly from your local filesystem without requiring them to be uploaded to a public URL first.

## Overview

Previously, scan2epub required PDF files to be accessible via public URLs because the Azure Content Understanding API only accepts URLs. This created friction for users who had to manually upload their PDF files to cloud storage services.

The new local PDF file support feature automatically handles this process by:
1. Detecting when the input is a local PDF file (vs. a URL)
2. Temporarily uploading the file to Azure Blob Storage
3. Processing the file using the temporary URL
4. Automatically cleaning up the temporary file after processing

## How It Works

### Architecture

```
Local PDF File → Azure Blob Storage → Azure Content Understanding → EPUB Output
                      ↓
                 Automatic Cleanup
```

### Components

1. **ConfigManager** (`config_manager.py`): Manages user configuration using INI format
2. **AzureStorageHandler** (`azure_storage_handler.py`): Handles Azure Blob Storage operations
3. **Updated scan2epub.py**: Main script with integrated local file support

## Configuration

### Environment Variables

Add the following to your `.env` file:

```env
# Azure Blob Storage Configuration (for local PDF file uploads)
AZURE_STORAGE_CONNECTION_STRING=your_storage_connection_string_here
```

### Configuration File

The new `scan2epub.ini` file allows easy configuration:

```ini
[Storage]
# Maximum file size in MB for local PDF uploads
max_file_size_mb = 256

# Name of the Azure Blob Storage container for temporary files
blob_container_name = scan2epub-temp

# How long (in hours) the temporary URLs should remain valid
sas_token_expiry_hours = 1

[Processing]
# Enable debug output for troubleshooting
debug = false

# Save interim results to disk to reduce memory usage
save_interim = false

[Cleanup]
# Always attempt to clean up temporary files, even if processing fails
cleanup_on_failure = true

# Log cleanup operations to track what was deleted
log_cleanup = true
```

## Usage

### Command Line Interface

The command line interface remains the same, but now accepts local PDF files:

```bash
# Local PDF file (NEW!)
python scan2epub.py my_book.pdf output.epub

# URL (existing functionality)
python scan2epub.py https://example.com/book.pdf output.epub

# With custom configuration
python scan2epub.py --config my_config.ini book.pdf output.epub

# OCR only with local file
python scan2epub.py --ocr-only book.pdf raw_output.epub

# Full pipeline with local file
python scan2epub.py book.pdf cleaned_output.epub
```

### New Command Line Options

- `--config PATH`: Path to configuration file (default: scan2epub.ini)
- `--language LANG`: Set OCR language (default: Hungarian)

## Azure Setup

### 1. Create Azure Blob Storage Account

1. Go to the Azure Portal
2. Create a new Storage Account
3. Choose "Standard" performance tier
4. Select "Cool" access tier for cost optimization

### 2. Get Connection String

1. Go to your Storage Account
2. Navigate to "Access keys"
3. Copy the connection string
4. Add it to your `.env` file

### 3. Container Creation

The tool automatically creates the `scan2epub-temp` container if it doesn't exist.

## Security Features

### SAS Tokens
- Temporary URLs with 1-hour expiration (configurable)
- Read-only permissions
- Automatic expiration prevents unauthorized access

### Automatic Cleanup
- Files are deleted immediately after processing
- Cleanup runs even if processing fails
- Orphaned files are prevented through session tracking

### File Size Limits
- Default 256MB limit (configurable)
- Prevents accidental large uploads
- Clear error messages for oversized files

## Error Handling

### Common Scenarios

1. **File too large**: Clear error message with actual vs. limit size
2. **Missing Azure Storage**: Only fails if local PDF files are used
3. **Upload failures**: Automatic retry with exponential backoff
4. **Cleanup failures**: Logged but doesn't fail the main process

### Error Messages

```bash
# File size error
Error: File too large: 300.5MB exceeds limit of 256.0MB

# Missing Azure Storage (only for local files)
Error: AZURE_STORAGE_CONNECTION_STRING must be set in environment variables
Azure Storage is required for local PDF files.

# Upload progress
Detected local PDF file: my_book.pdf
Uploading my_book.pdf (45.2MB) to Azure...
Upload complete: 20250111_143022_my_book.pdf
```

## Cost Optimization

### Storage Costs
- Uses "Cool" tier for temporary storage (cheaper)
- Files are deleted within 1 hour
- Typical cost: $0.01-0.05 per book

### Recommendations
- Process files individually rather than in batches
- Use the file size limit to prevent unexpected costs
- Monitor Azure costs through the Azure Portal

## Troubleshooting

### Debug Mode
Enable debug mode for detailed logging:

```bash
python scan2epub.py --debug book.pdf output.epub
```

### Configuration Issues
1. Check `.env` file exists and has correct connection string
2. Verify Azure Storage account is accessible
3. Ensure container permissions are correct

### Upload Issues
1. Check internet connection
2. Verify file isn't corrupted
3. Try with a smaller test file first

## Migration from URL-based Workflow

### Before (URL required)
```bash
# User had to manually upload to cloud storage
# Then use the public URL
python scan2epub.py https://mycloud.com/book.pdf output.epub
```

### After (Local files supported)
```bash
# Direct local file processing
python scan2epub.py book.pdf output.epub
```

### Backward Compatibility
- URL-based processing still works exactly as before
- No changes needed for existing workflows
- New functionality is additive only

## Technical Details

### File Naming Convention
Temporary files use the format: `YYYYMMDD_HHMMSS_originalname.pdf`

### SAS Token Permissions
- Read-only access
- 1-hour expiration (configurable)
- Container-scoped (not account-scoped)

### Cleanup Process
1. Track all uploaded files in session
2. Delete files in `finally` block
3. Log success/failure of each deletion
4. Continue processing even if cleanup fails

## Future Enhancements

### Planned Features
- Batch processing of multiple local files
- Resume capability for interrupted uploads
- Integration with other cloud storage providers
- Local caching of frequently processed files

### Configuration Enhancements
- Per-file size limits
- Custom cleanup schedules
- Advanced retry policies
- Cost monitoring integration

## Support

### Getting Help
- Check the debug output first
- Review Azure Portal for storage issues
- Verify all environment variables are set
- Test with a small file first

### Reporting Issues
Include the following information:
- File size and type
- Configuration settings (without sensitive data)
- Full error message
- Debug output (if available)
