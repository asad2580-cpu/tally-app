import json
import logging
import os
from typing import List, Dict, Any, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel
from PIL import Image
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Transaction(BaseModel):
    date: str
    narration: str
    debit_amount: Optional[str] = None
    credit_amount: Optional[str] = None
    running_balance: str

class TransactionExtractor:
    def __init__(self):
        """Initialize the transaction extractor with Gemini client."""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        self.client = genai.Client(api_key=api_key)
        
    def extract_transactions(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Extract transaction data from bank statement image.
        
        Args:
            image_bytes: PNG image data as bytes
            
        Returns:
            List of transaction dictionaries
        """
        try:
            # Streamlined prompt for faster processing
            prompt = """Extract all transactions from this bank statement as JSON array.

Required fields per transaction:
- date: Transaction date (YYYY-MM-DD preferred)
- narration: Description/details 
- debit_amount: Debit amount (number only, null if none)
- credit_amount: Credit amount (number only, null if none)
- running_balance: Balance after transaction (number only)

Return only valid JSON array. Include all visible transactions in chronological order."""

            # Optimize image before processing
            optimized_image_bytes = self._optimize_image(image_bytes)
            
            # Generate content with image analysis using faster model
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(
                        data=optimized_image_bytes,
                        mime_type="image/png",
                    ),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )

            if not response.text:
                logger.error("Empty response from Gemini API")
                return []

            # Parse the JSON response
            try:
                transactions_data = json.loads(response.text)
                
                # Validate and clean the data
                if isinstance(transactions_data, list):
                    cleaned_transactions = []
                    for transaction in transactions_data:
                        if isinstance(transaction, dict):
                            cleaned_transaction = self._clean_transaction_data(transaction)
                            if cleaned_transaction:
                                cleaned_transactions.append(cleaned_transaction)
                    
                    logger.info(f"Successfully extracted {len(cleaned_transactions)} transactions")
                    return cleaned_transactions
                else:
                    logger.error("Response is not a list of transactions")
                    return []
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error extracting transactions: {e}")
            raise Exception(f"Failed to extract transactions: {str(e)}")

    def _clean_transaction_data(self, transaction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Clean and validate transaction data.
        
        Args:
            transaction: Raw transaction dictionary
            
        Returns:
            Cleaned transaction dictionary or None if invalid
        """
        try:
            # Required fields
            date = str(transaction.get('date', '')).strip()
            narration = str(transaction.get('narration', '')).strip()
            running_balance = str(transaction.get('running_balance', '')).strip()
            
            # Optional amount fields
            debit_amount = transaction.get('debit_amount')
            credit_amount = transaction.get('credit_amount')
            
            # Skip if essential fields are missing
            if not date or not narration:
                logger.warning(f"Skipping transaction with missing essential fields: {transaction}")
                return None
            
            # Clean amount fields
            cleaned_debit = self._clean_amount(debit_amount)
            cleaned_credit = self._clean_amount(credit_amount)
            cleaned_balance = self._clean_amount(running_balance)
            
            cleaned_transaction = {
                'date': date,
                'narration': narration,
                'debit_amount': cleaned_debit,
                'credit_amount': cleaned_credit,
                'running_balance': cleaned_balance or '0'
            }
            
            return cleaned_transaction
            
        except Exception as e:
            logger.error(f"Error cleaning transaction data: {e}")
            return None

    def _clean_amount(self, amount: Any) -> Optional[str]:
        """
        Clean and validate amount field.
        
        Args:
            amount: Raw amount value
            
        Returns:
            Cleaned amount string or None
        """
        if amount is None or amount == '':
            return None
            
        # Convert to string and clean
        amount_str = str(amount).strip()
        
        # Remove common currency symbols and formatting
        amount_str = amount_str.replace('₹', '').replace('$', '').replace(',', '').strip()
        
        # Handle empty or null values
        if not amount_str or amount_str.lower() in ['null', 'none', '-', '']:
            return None
            
        try:
            # Validate that it's a valid number
            float(amount_str)
            return amount_str
        except ValueError:
            logger.warning(f"Invalid amount format: {amount}")
            return None

    def extract_transactions_with_retry(self, image_bytes: bytes, max_retries: int = 2) -> List[Dict[str, Any]]:
        """
        Extract transactions with retry logic.
        
        Args:
            image_bytes: PNG image data as bytes
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of transaction dictionaries
        """
        for attempt in range(max_retries + 1):
            try:
                transactions = self.extract_transactions(image_bytes)
                if transactions:  # If we got results, return them
                    return transactions
                elif attempt < max_retries:  # If no results but we have retries left
                    logger.info(f"No transactions found, retrying... (attempt {attempt + 1})")
                    continue
                else:  # Final attempt with no results
                    logger.warning("No transactions found after all retry attempts")
                    return []
                    
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    continue
                else:
                    logger.error(f"All attempts failed. Final error: {e}")
                    raise e
                    
        return []

    def _optimize_image(self, image_bytes: bytes) -> bytes:
        """
        Optimize image for faster AI processing while maintaining accuracy.
        
        Args:
            image_bytes: Original image bytes
            
        Returns:
            Optimized image bytes
        """
        try:
            # Open the image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if needed (for consistent processing)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Get original dimensions
            width, height = image.size
            
            # Calculate optimal size (max 2048px on longer side for good balance of speed/accuracy)
            max_dimension = 2048
            if max(width, height) > max_dimension:
                if width > height:
                    new_width = max_dimension
                    new_height = int(height * (max_dimension / width))
                else:
                    new_height = max_dimension
                    new_width = int(width * (max_dimension / height))
                
                # Resize with high-quality resampling
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"Resized image from {width}x{height} to {new_width}x{new_height}")
            
            # Save optimized image to bytes
            output_bytes = io.BytesIO()
            image.save(output_bytes, format='PNG', optimize=True)
            return output_bytes.getvalue()
            
        except Exception as e:
            logger.warning(f"Image optimization failed: {e}. Using original image.")
            return image_bytes
