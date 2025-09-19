# Bank Statement Transaction Extractor

## Overview

This is a Streamlit-based web application that uses AI to extract transaction data from bank statement images and generate Tally-compatible XML files for accounting software integration. The application leverages Google's Gemini AI to perform optical character recognition and structured data extraction from PNG bank statement images, then formats the extracted transactions into XML that can be imported directly into Tally accounting software.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit web framework for rapid prototyping and deployment
- **User Interface**: Simple form-based interface with file upload capabilities
- **Layout**: Wide layout configuration with columnar organization for configuration inputs
- **Caching**: Streamlit's `@st.cache_resource` decorator for efficient resource management

### Backend Architecture
- **Core Components**:
  - `TransactionExtractor`: Handles AI-powered data extraction from images
  - `TallyXMLGenerator`: Converts extracted data to Tally-compatible XML format
- **Data Processing Pipeline**:
  1. Image upload and validation (PNG format)
  2. AI-powered transaction extraction using Gemini
  3. Data structuring using Pydantic models
  4. XML generation for Tally import
- **Error Handling**: Environment variable validation and user-friendly error messages

### Data Models
- **Transaction Schema**: Pydantic model with fields for date, narration, debit/credit amounts, and running balance
- **XML Structure**: Tally-specific envelope format with proper headers and data organization
- **Configuration**: Company name and bank ledger mapping for Tally integration

### AI Integration
- **Provider**: Google Gemini AI for optical character recognition and data extraction
- **Input Processing**: Accepts PNG image format for bank statements
- **Output Formatting**: Structured JSON extraction with specific field mapping
- **Prompt Engineering**: Specialized prompts for financial document processing

## External Dependencies

### AI Services
- **Google Gemini API**: Primary AI service for image analysis and text extraction
  - Requires `GEMINI_API_KEY` environment variable
  - Used for OCR and structured data extraction from bank statement images

### Python Libraries
- **Streamlit**: Web application framework for user interface
- **Pydantic**: Data validation and modeling for transaction structures
- **PIL (Pillow)**: Image processing and manipulation
- **xml.etree.ElementTree**: XML generation for Tally import format

### Accounting Software Integration
- **Tally**: Target accounting software for XML import
  - Requires company name configuration
  - Requires bank ledger name mapping
  - Uses suspense ledger for unmatched transactions