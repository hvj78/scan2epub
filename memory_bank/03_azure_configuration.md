# Azure Configuration

## Required Azure Services

### 1. Azure AI Content Understanding
Used for OCR processing of PDF documents.

**Service Details:**
- Service Type: Azure AI Content Understanding
- API Version: `2025-05-01-preview`
- Analyzer ID: `prebuilt-documentAnalyzer`
- Endpoint Format: `https://your-content-understanding-resource-name.services.ai.azure.com/`

**Required Permissions:**
- Read access to Content Understanding API
- Ability to submit analyze requests
- Access to retrieve analysis results

### 2. Azure OpenAI Service
Used for text cleanup and optimization with GPT-4.

**Service Details:**
- Service Type: Azure OpenAI
- Model: GPT-4 (deployment required)
- API Version: `2024-02-15-preview`
- Endpoint Format: `https://your-resource-name.openai.azure.com/`

**Required Setup:**
- Create an Azure OpenAI resource
- Deploy a GPT-4 model
- Note the deployment name for configuration

## Environment Configuration

### Setting Up .env File

1. Copy `.env.template` to `.env`:
   ```bash
   cp .env.template .env
   ```

2. Fill in the required values:

```env
# Azure AI Content Understanding Configuration
AZURE_CU_API_KEY=your_content_understanding_api_key_here
AZURE_CU_ENDPOINT=https://your-content-understanding-resource-name.services.ai.azure.com/

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=your_gpt4_deployment_name

# Processing Configuration (Optional - defaults shown)
MAX_TOKENS_PER_CHUNK=3000
TEMPERATURE=0.1
MAX_TOKENS_RESPONSE=4000
MAX_RETRIES=3
RETRY_DELAY=2
```

### Configuration Parameters Explained

#### Azure AI Content Understanding
- **AZURE_CU_API_KEY**: Your subscription key for Content Understanding service
- **AZURE_CU_ENDPOINT**: The full endpoint URL for your Content Understanding resource

#### Azure OpenAI
- **AZURE_OPENAI_API_KEY**: Your Azure OpenAI subscription key
- **AZURE_OPENAI_ENDPOINT**: The full endpoint URL for your Azure OpenAI resource
- **AZURE_OPENAI_API_VERSION**: API version to use (keep default unless newer available)
- **AZURE_OPENAI_DEPLOYMENT_NAME**: The name you gave your GPT-4 deployment

#### Processing Parameters
- **MAX_TOKENS_PER_CHUNK**: Maximum tokens per text chunk sent to GPT-4
  - Default: 3000
  - Adjust based on your needs and token limits
  
- **TEMPERATURE**: Controls randomness in GPT-4 responses
  - Default: 0.1 (low randomness for consistency)
  - Range: 0.0 to 1.0
  
- **MAX_TOKENS_RESPONSE**: Maximum tokens in GPT-4 response
  - Default: 4000
  - Must not exceed your deployment's limit
  
- **MAX_RETRIES**: Number of retry attempts for failed API calls
  - Default: 3
  - Increase for unreliable connections
  
- **RETRY_DELAY**: Seconds to wait between retries
  - Default: 2
  - Increase if hitting rate limits

## Azure Setup Guide

### Step 1: Create Azure AI Content Understanding Resource

1. Go to Azure Portal
2. Create a new "Content Understanding" resource
3. Choose your subscription and resource group
4. Select a region (choose closest for best performance)
5. Choose pricing tier based on your needs
6. After creation, go to "Keys and Endpoint"
7. Copy the KEY 1 and Endpoint values

### Step 2: Create Azure OpenAI Resource

1. In Azure Portal, create "Azure OpenAI" resource
2. Select subscription and resource group
3. Choose region (limited availability)
4. Select pricing tier
5. After creation, go to "Keys and Endpoint"
6. Copy the KEY 1 and Endpoint values

### Step 3: Deploy GPT-4 Model

1. In your Azure OpenAI resource, go to "Model deployments"
2. Click "Create new deployment"
3. Select model: gpt-4 (or gpt-4-32k for longer contexts)
4. Give it a deployment name (e.g., "gpt-4-cleanup")
5. Set tokens per minute rate limit based on your needs
6. Deploy and note the deployment name

## Cost Considerations

### Azure AI Content Understanding
- Charged per page analyzed
- Pricing varies by region and volume
- Consider batch processing for cost efficiency

### Azure OpenAI GPT-4
- Charged per 1,000 tokens (input + output)
- GPT-4 is more expensive than GPT-3.5
- Monitor usage to control costs
- Consider using GPT-3.5-turbo for testing

### Cost Optimization Tips
1. Process books in batches during off-peak hours
2. Use --ocr-only mode to test OCR quality before cleanup
3. Start with small test files to verify configuration
4. Monitor Azure cost analysis regularly
5. Set up cost alerts in Azure Portal

## Troubleshooting

### Common Issues

1. **"Missing required environment variables"**
   - Ensure .env file exists and contains all required keys
   - Check for typos in variable names
   - Verify no extra spaces around values

2. **"401 Unauthorized" errors**
   - Verify API keys are correct
   - Check if keys have been regenerated
   - Ensure resource is not disabled

3. **"404 Not Found" for endpoints**
   - Verify endpoint URLs include trailing slash
   - Check region is correct
   - Ensure deployment name matches exactly

4. **Rate limiting errors**
   - Increase RETRY_DELAY value
   - Reduce MAX_TOKENS_PER_CHUNK
   - Check Azure quota limits

5. **Memory issues with large EPUBs**
   - Use --save-interim flag
   - Process smaller sections
   - Increase system memory

### Validation Steps

1. Test Content Understanding:
   ```bash
   python pdf_ocr_processor.py
   ```
   (Update sample URL in the file first)

2. Test full pipeline with small PDF:
   ```bash
   python scan2epub.py https://example.com/small.pdf test.epub
   ```

3. Check Azure logs for detailed error information
