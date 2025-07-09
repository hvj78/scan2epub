# Azure AI Content Understanding Setup Guide

This document provides a step-by-step guide on how to set up Azure AI Content Understanding in your Azure subscription, obtain the necessary API key and endpoint, and configure your environment for the `scan2epub` tool.

## Prerequisites

- An active Azure subscription. If you don't have one, you can [create one for free](https://azure.microsoft.com/free/).
- Basic understanding of Azure Portal navigation.

## Step 1: Create an Azure AI Foundry Resource

Azure AI Content Understanding is part of the Azure AI Foundry service. You need to create an AI Foundry resource to use Content Understanding.

1. **Log in to Azure Portal**: Go to [portal.azure.com](https://portal.azure.com/) and sign in with your Azure account.

2. **Search for "AI Foundry"**: In the search bar at the top of the portal, type "AI Foundry" and select "AI Foundry" from the services results.

3. **Create AI Foundry Resource**:
   
   - Click on the "Create" button.
   - Fill in the required details:
     - **Subscription**: Select your Azure subscription.
     - **Resource Group**: Choose an existing resource group or create a new one. A resource group is a logical container for Azure resources.
     - **Region**: Select a region that supports Azure AI Foundry. Choose a region geographically close to you for lower latency.
     - **Name**: Enter a unique name for your AI Foundry resource.
     - **Pricing Tier**: Select the appropriate pricing tier. For testing and development, "Standard" is usually sufficient.
   - Review your selections and click "Review + create", then "Create".

4. **Deployment**: Wait for the deployment to complete. This may take a few minutes.

## Step 2: Obtain API Key and Endpoint

Once your Azure AI Foundry resource is deployed, you need to get its API key and endpoint to use it with the `scan2epub` tool.

1. **Navigate to your Resource**: After deployment, click "Go to resource" or find your newly created AI Foundry resource in the Azure Portal.

2. **Access Keys and Endpoint**:
   
   - In the left-hand menu of your AI Foundry resource, under "Resource Management", click on "Keys and Endpoint".
   - You will see two keys (Key 1 and Key 2) and the Endpoint URL.
   - **Copy one of the keys** (e.g., Key 1). This will be your `AZURE_CU_API_KEY`.
   - **Copy the Endpoint URL**. This will be your `AZURE_CU_ENDPOINT`.
   
   **Example Endpoint Format**: `https://your-resource-name.services.ai.azure.com/`

## Step 3: Configure `scan2epub` Environment Variables

The `scan2epub` tool uses environment variables to connect to Azure AI services.

1. **Locate `.env.template`**: In the root directory of the `scan2epub` project, find the file named `.env.template`.

2. **Create `.env` file**: Make a copy of `.env.template` and rename it to `.env`. This file will store your sensitive credentials and should not be committed to version control.

3. **Edit `.env` file**: Open the newly created `.env` file and update the following lines with the values you obtained in Step 2:
   
   ```dotenv
   # Azure AI Content Understanding Configuration
   AZURE_CU_API_KEY=your_content_understanding_api_key_here
   AZURE_CU_ENDPOINT=https://your-content-understanding-resource-name.services.ai.azure.com/
   ```
   
   Make sure to replace `your_content_understanding_api_key_here` and `https://your-content-understanding-resource-name.services.ai.azure.com/` with your actual key and endpoint.
   
   You will also need to ensure your Azure OpenAI configuration is correctly set in this file if you plan to use the cleanup functionality.

## Next Steps

Once you have completed these steps, your `scan2epub` tool will be configured to use Azure AI Content Understanding for OCR processing. You can now proceed with running the `scan2epub.py` script.
