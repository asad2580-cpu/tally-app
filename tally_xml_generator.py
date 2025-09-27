import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TallyXMLGenerator:
    def __init__(self, company_name: str, bank_ledger_name: str):
        """
        Initialize Tally XML generator.
        
        Args:
            company_name: Name of the company in Tally
            bank_ledger_name: Name of the bank ledger in Tally
        """
        self.company_name = company_name
        self.bank_ledger_name = bank_ledger_name
        self.suspense_ledger_name = "Suspense"
        
    def generate_xml(self, transactions: List[Dict[str, Any]]) -> str:
        """
        Generate Tally XML for bank transactions.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            XML string ready for Tally import
        """
        # Create root envelope
        envelope = ET.Element("ENVELOPE")
        
        # Header
        header = ET.SubElement(envelope, "HEADER")
        ET.SubElement(header, "TALLYREQUEST").text = "Import Data"
        ET.SubElement(header, "TYPE").text = "Data"
        ET.SubElement(header, "ID").text = "Vouchers"
        
        # Body
        body = ET.SubElement(envelope, "BODY")
        import_data = ET.SubElement(body, "IMPORTDATA")
        
        # Request description
        request_desc = ET.SubElement(import_data, "REQUESTDESC")
        ET.SubElement(request_desc, "REPORTNAME").text = "Vouchers"
        static_vars = ET.SubElement(request_desc, "STATICVARIABLES")
        ET.SubElement(static_vars, "SVCURRENTCOMPANY").text = self.company_name
        
        # Request data
        request_data = ET.SubElement(import_data, "REQUESTDATA")
        
        # Create Suspense ledger if it doesn't exist
        self._add_suspense_ledger(request_data)
        
        # Add transactions as vouchers
        voucher_number = 1
        for transaction in transactions:
            self._add_transaction_voucher(request_data, transaction, voucher_number)
            voucher_number += 1
        
        # Convert to string with proper formatting
        return self._prettify_xml(envelope)
    
    def _add_suspense_ledger(self, parent: ET.Element):
        """Add Suspense ledger creation to XML."""
        tally_message = ET.SubElement(parent, "TALLYMESSAGE")
        tally_message.set("xmlns:UDF", "TallyUDF")
        
        ledger = ET.SubElement(tally_message, "LEDGER")
        ledger.set("NAME", self.suspense_ledger_name)
        ledger.set("ACTION", "Create")
        
        ET.SubElement(ledger, "PARENT").text = "Suspense A/c"
        ET.SubElement(ledger, "ISBILLWISEON").text = "No"
        ET.SubElement(ledger, "ISCOSTCENTRESON").text = "No"
        
    def _add_transaction_voucher(self, parent: ET.Element, transaction: Dict[str, Any], voucher_number: int):
        """Add a single transaction as a voucher."""
        tally_message = ET.SubElement(parent, "TALLYMESSAGE")
        tally_message.set("xmlns:UDF", "TallyUDF")
        
        # Determine voucher type and amounts
        debit_amount = self._parse_amount(transaction.get('debit_amount'))
        credit_amount = self._parse_amount(transaction.get('credit_amount'))
        
        if credit_amount > 0:
            # Money came into bank (Receipt) - Debit bank account
            voucher_type = "Receipt"
            transaction_amount = credit_amount
            bank_is_debit = True  # Money coming in = debit bank
        elif debit_amount > 0:
            # Money went out of bank (Payment) - Credit bank account  
            voucher_type = "Payment"
            transaction_amount = debit_amount
            bank_is_debit = False  # Money going out = credit bank
        else:
            # Skip transactions with no amount
            return
        
        voucher = ET.SubElement(tally_message, "VOUCHER")
        voucher.set("VCHTYPE", voucher_type)
        voucher.set("ACTION", "Create")
        
        # Voucher details
        transaction_date = self._format_date(transaction.get('date', ''))
        ET.SubElement(voucher, "DATE").text = transaction_date
        ET.SubElement(voucher, "VOUCHERTYPENAME").text = voucher_type
        ET.SubElement(voucher, "VOUCHERNUMBER").text = str(voucher_number)
        ET.SubElement(voucher, "NARRATION").text = transaction.get('narration', '')[:250]  # Limit length
        
        # Bank ledger entry
        bank_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(bank_entry, "LEDGERNAME").text = self.bank_ledger_name
        ET.SubElement(bank_entry, "ISDEEMEDPOSITIVE").text = "No" if bank_is_debit else "Yes"
        ET.SubElement(bank_entry, "AMOUNT").text = f"{transaction_amount:.2f}"
        
        # Suspense ledger entry (opposite of bank)
        suspense_entry = ET.SubElement(voucher, "ALLLEDGERENTRIES.LIST")
        ET.SubElement(suspense_entry, "LEDGERNAME").text = self.suspense_ledger_name
        ET.SubElement(suspense_entry, "ISDEEMEDPOSITIVE").text = "Yes" if bank_is_debit else "No"
        ET.SubElement(suspense_entry, "AMOUNT").text = f"{transaction_amount:.2f}"
    
    def _parse_amount(self, amount_str: Any) -> float:
        """Parse amount string to float."""
        if not amount_str:
            return 0.0
        try:
            # Remove currency symbols and commas
            amount_str = str(amount_str).replace('₹', '').replace(',', '').strip()
            return float(amount_str) if amount_str else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def _format_date(self, date_str: str) -> str:
        """Format date for Tally (YYYYMMDD)."""
        if not date_str:
            return datetime.now().strftime("%Y%m%d")
        
        try:
            # Try common date formats
            for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y%m%d")
                except ValueError:
                    continue
            
            # If parsing fails, use current date
            logger.warning(f"Could not parse date: {date_str}, using current date")
            return datetime.now().strftime("%Y%m%d")
            
        except Exception as e:
            logger.error(f"Error formatting date {date_str}: {e}")
            return datetime.now().strftime("%Y%m%d")
    
    def _prettify_xml(self, element: ET.Element) -> str:
        """Convert XML element to prettified string."""
        # Create XML declaration and format
        xml_str = ET.tostring(element, encoding='unicode')
        
        # Add XML declaration
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
        
        # Basic prettification (simple indentation)
        lines = xml_str.split('>')
        formatted_lines = []
        indent_level = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('</'):
                indent_level -= 1
            
            formatted_lines.append('  ' * indent_level + line + '>')
            
            if not line.startswith('</') and not line.endswith('/>') and not any(line.startswith(f'<{tag}') and f'</{tag}>' in line for tag in ['TALLYREQUEST', 'TYPE', 'ID', 'REPORTNAME', 'SVCURRENTCOMPANY', 'PARENT', 'ISBILLWISEON', 'ISCOSTCENTRESON', 'DATE', 'VOUCHERTYPENAME', 'VOUCHERNUMBER', 'NARRATION', 'LEDGERNAME', 'ISDEEMEDPOSITIVE', 'AMOUNT']):
                indent_level += 1
        
        formatted_xml = xml_declaration + '\n'.join(formatted_lines)
        
        # Remove the extra > at the end
        formatted_xml = formatted_xml.replace('>>', '>')
        
        return formatted_xml

    def validate_xml_structure(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate transaction data before XML generation.
        
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'transaction_count': len(transactions)
        }
        
        if not transactions:
            validation_result['valid'] = False
            validation_result['errors'].append("No transactions provided")
            return validation_result
        
        if not self.company_name.strip():
            validation_result['valid'] = False
            validation_result['errors'].append("Company name is required")
        
        if not self.bank_ledger_name.strip():
            validation_result['valid'] = False
            validation_result['errors'].append("Bank ledger name is required")
        
        # Validate individual transactions
        for i, transaction in enumerate(transactions):
            if not transaction.get('narration'):
                validation_result['warnings'].append(f"Transaction {i+1}: Missing narration")
            
            debit = self._parse_amount(transaction.get('debit_amount'))
            credit = self._parse_amount(transaction.get('credit_amount'))
            
            if debit == 0 and credit == 0:
                validation_result['warnings'].append(f"Transaction {i+1}: No amount specified")
            
            if debit > 0 and credit > 0:
                validation_result['warnings'].append(f"Transaction {i+1}: Both debit and credit amounts present")
        
        return validation_result