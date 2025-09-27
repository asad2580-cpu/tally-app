import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GSTTransaction:
    """Represents a GST transaction from return data."""
    date: str
    party_name: str
    party_gstin: str
    party_state: str
    invoice_number: str
    invoice_date: str
    taxable_value: float
    igst_amount: float
    cgst_amount: float
    sgst_amount: float
    total_tax: float
    invoice_value: float
    is_interstate: bool
    transaction_type: str  # 'purchase' or 'sales'

class GSTProcessor:
    """Process GST return JSON files to extract transaction data."""
    
    def __init__(self, company_state: str):
        """
        Initialize GST processor.
        
        Args:
            company_state: State of the company for interstate determination
        """
        self.company_state = company_state
        
        # State code mapping for GST bifurcation
        self.state_codes = {
            "Andhra Pradesh": "37", "Arunachal Pradesh": "12", "Assam": "18", "Bihar": "10",
            "Chhattisgarh": "22", "Goa": "30", "Gujarat": "24", "Haryana": "06", 
            "Himachal Pradesh": "02", "Jharkhand": "20", "Karnataka": "29", "Kerala": "32",
            "Madhya Pradesh": "23", "Maharashtra": "27", "Manipur": "14", "Meghalaya": "17",
            "Mizoram": "15", "Nagaland": "13", "Odisha": "21", "Punjab": "03", "Rajasthan": "08",
            "Sikkim": "11", "Tamil Nadu": "33", "Telangana": "36", "Tripura": "16",
            "Uttar Pradesh": "09", "Uttarakhand": "05", "West Bengal": "19", "Delhi": "07",
            "Puducherry": "34"
        }
    
    def process_gstr2b(self, json_data: Dict[str, Any]) -> List[GSTTransaction]:
        """
        Process GSTR2B JSON data to extract purchase transactions.
        GSTR2B has Parts A, B, C, D structure from GST portal.
        
        Args:
            json_data: GSTR2B JSON data from GST portal
            
        Returns:
            List of GST transactions
        """
        transactions = []
        
        try:
            logger.info("Processing GSTR2B - Static ITC statement")
            
            # GSTR2B has different structure with Parts A, B, C, D
            # Part A: ITC Available - Inward supplies from registered suppliers
            if 'itc_avl' in json_data:
                part_a = json_data['itc_avl']
                
                # Process B2B invoices in Part A
                if 'b2b' in part_a:
                    for supplier_data in part_a['b2b']:
                        supplier_gstin = supplier_data.get('gstin', '')
                        supplier_state = self._get_state_from_gstin(supplier_gstin)
                        
                        for invoice in supplier_data.get('inv', []):
                            transaction = self._process_gstr2b_b2b_invoice(
                                invoice, supplier_gstin, supplier_state
                            )
                            if transaction:
                                transactions.append(transaction)
                
                # Process Import data in Part A
                if 'impg' in part_a:
                    for import_data in part_a['impg']:
                        transaction = self._process_gstr2b_import_transaction(import_data)
                        if transaction:
                            transactions.append(transaction)
            
            # Part B: ISD Credits Received
            if 'isd_credit' in json_data:
                for isd_data in json_data['isd_credit']:
                    transaction = self._process_gstr2b_isd_transaction(isd_data)
                    if transaction:
                        transactions.append(transaction)
            
            logger.info(f"Processed GSTR2B: {len(transactions)} purchase transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"Error processing GSTR2B: {e}")
            return []
    
    def process_gstr1(self, json_data: Dict[str, Any]) -> List[GSTTransaction]:
        """
        Process GSTR1 JSON data to extract sales transactions.
        Based on actual GST portal format: {"version": "GST1.1", "gstin": "...", "fp": "...", "b2b": [], "b2cs": [], "hsn": []}
        
        Args:
            json_data: GSTR1 JSON data from GST portal
            
        Returns:
            List of GST transactions
        """
        transactions = []
        
        try:
            # GSTR1 has direct structure with b2b, b2cs, hsn at root level
            logger.info(f"Processing GSTR1 with version: {json_data.get('version', 'Unknown')}")
            
            # Process B2B sales (Business to Business)
            if 'b2b' in json_data:
                for customer_data in json_data['b2b']:
                    customer_gstin = customer_data.get('ctin', '')
                    customer_state = self._get_state_from_gstin(customer_gstin)
                    
                    for invoice in customer_data.get('inv', []):
                        transaction = self._process_gstr1_b2b_invoice(
                            invoice, customer_gstin, customer_state
                        )
                        if transaction:
                            transactions.append(transaction)
            
            # Process B2CS sales (Business to Consumer - Small)
            if 'b2cs' in json_data:
                for b2cs_data in json_data['b2cs']:
                    transaction = self._process_gstr1_b2cs_transaction(b2cs_data)
                    if transaction:
                        transactions.append(transaction)
            
            logger.info(f"Processed GSTR1: {len(transactions)} sales transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"Error processing GSTR1: {e}")
            return []
    
    def process_gstr2a(self, json_data: Dict[str, Any]) -> List[GSTTransaction]:
        """
        Process GSTR2A JSON data to extract purchase transactions.
        GSTR2A is auto-generated and similar to GSTR2B but with different structure.
        
        Args:
            json_data: GSTR2A JSON data from GST portal
            
        Returns:
            List of GST transactions
        """
        transactions = []
        
        try:
            logger.info("Processing GSTR2A - Auto-drafted inward supplies")
            
            # GSTR2A typically has b2b, b2ba (amendments), cdnr (credit/debit notes) sections
            # Process B2B invoices
            if 'b2b' in json_data:
                for supplier_data in json_data['b2b']:
                    supplier_gstin = supplier_data.get('ctin', '')
                    supplier_state = self._get_state_from_gstin(supplier_gstin)
                    
                    for invoice in supplier_data.get('inv', []):
                        transaction = self._process_gstr2a_b2b_invoice(
                            invoice, supplier_gstin, supplier_state
                        )
                        if transaction:
                            transactions.append(transaction)
            
            # Process Import data
            if 'impg' in json_data:
                for import_data in json_data['impg']:
                    transaction = self._process_gstr2a_import_transaction(import_data)
                    if transaction:
                        transactions.append(transaction)
            
            logger.info(f"Processed GSTR2A: {len(transactions)} purchase transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"Error processing GSTR2A: {e}")
            return []

    def _process_gstr1_b2b_invoice(self, invoice: Dict[str, Any], customer_gstin: str, 
                                 customer_state: str) -> Optional[GSTTransaction]:
        """Process a B2B invoice from GSTR1 format."""
        try:
            invoice_number = invoice.get('inum', '')
            invoice_date = invoice.get('idt', '')
            invoice_value = float(invoice.get('val', 0))
            pos = invoice.get('pos', '')  # Place of supply
            
            # Process items with correct GSTR1 structure
            total_taxable = 0
            total_igst = 0
            total_cgst = 0
            total_sgst = 0
            
            for item in invoice.get('itms', []):
                # GSTR1 has itm_det directly under itms
                itm_det = item.get('itm_det', {})
                total_taxable += float(itm_det.get('txval', 0))
                total_igst += float(itm_det.get('iamt', 0))
                total_cgst += float(itm_det.get('camt', 0))
                total_sgst += float(itm_det.get('samt', 0))
            
            total_tax = total_igst + total_cgst + total_sgst
            is_interstate = total_igst > 0 or customer_state != self.company_state
            
            party_name = f"Customer-{customer_gstin[:10]}" if customer_gstin else "Unknown Customer"
            
            return GSTTransaction(
                date=self._format_date(invoice_date),
                party_name=party_name,
                party_gstin=customer_gstin,
                party_state=customer_state,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                taxable_value=total_taxable,
                igst_amount=total_igst,
                cgst_amount=total_cgst,
                sgst_amount=total_sgst,
                total_tax=total_tax,
                invoice_value=invoice_value,
                is_interstate=is_interstate,
                transaction_type='sales'
            )
            
        except Exception as e:
            logger.error(f"Error processing GSTR1 B2B invoice: {e}")
            return None

    def _process_gstr1_b2cs_transaction(self, b2cs_data: Dict[str, Any]) -> Optional[GSTTransaction]:
        """Process B2CS transaction from GSTR1 format."""
        try:
            supply_type = b2cs_data.get('sply_ty', '')  # INTER/INTRA
            pos = b2cs_data.get('pos', '')  # Place of supply
            typ = b2cs_data.get('typ', '')  # OE/E
            rate = float(b2cs_data.get('rt', 0))
            
            total_taxable = float(b2cs_data.get('txval', 0))
            total_igst = float(b2cs_data.get('iamt', 0))
            total_cgst = float(b2cs_data.get('camt', 0))
            total_sgst = float(b2cs_data.get('samt', 0))
            
            total_tax = total_igst + total_cgst + total_sgst
            total_value = total_taxable + total_tax
            is_interstate = supply_type == 'INTER' or total_igst > 0
            
            return GSTTransaction(
                date=datetime.now().strftime("%Y-%m-%d"),
                party_name=f"B2CS-{supply_type}-{pos}",
                party_gstin="",
                party_state=pos,
                invoice_number=f"B2CS-{supply_type}-Consolidated",
                invoice_date="",
                taxable_value=total_taxable,
                igst_amount=total_igst,
                cgst_amount=total_cgst,
                sgst_amount=total_sgst,
                total_tax=total_tax,
                invoice_value=total_value,
                is_interstate=is_interstate,
                transaction_type='sales'
            )
            
        except Exception as e:
            logger.error(f"Error processing GSTR1 B2CS transaction: {e}")
            return None

    def _process_gstr2b_b2b_invoice(self, invoice: Dict[str, Any], supplier_gstin: str, 
                                  supplier_state: str) -> Optional[GSTTransaction]:
        """Process a B2B invoice from GSTR2B format."""
        try:
            invoice_number = invoice.get('inum', '')
            invoice_date = invoice.get('idt', '')
            invoice_value = float(invoice.get('val', 0))
            
            # GSTR2B structure for items
            total_taxable = 0
            total_igst = 0
            total_cgst = 0
            total_sgst = 0
            
            for item in invoice.get('items', []):
                total_taxable += float(item.get('txval', 0))
                total_igst += float(item.get('iamt', 0))
                total_cgst += float(item.get('camt', 0))
                total_sgst += float(item.get('samt', 0))
            
            total_tax = total_igst + total_cgst + total_sgst
            is_interstate = total_igst > 0 or supplier_state != self.company_state
            
            party_name = f"Supplier-{supplier_gstin[:10]}" if supplier_gstin else "Unknown Supplier"
            
            return GSTTransaction(
                date=self._format_date(invoice_date),
                party_name=party_name,
                party_gstin=supplier_gstin,
                party_state=supplier_state,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                taxable_value=total_taxable,
                igst_amount=total_igst,
                cgst_amount=total_cgst,
                sgst_amount=total_sgst,
                total_tax=total_tax,
                invoice_value=invoice_value,
                is_interstate=is_interstate,
                transaction_type='purchase'
            )
            
        except Exception as e:
            logger.error(f"Error processing GSTR2B B2B invoice: {e}")
            return None

    def _process_gstr2b_import_transaction(self, import_data: Dict[str, Any]) -> Optional[GSTTransaction]:
        """Process import transaction from GSTR2B format."""
        try:
            port_code = import_data.get('port_code', '')
            bill_num = import_data.get('bill_num', '')
            bill_date = import_data.get('bill_date', '')
            
            total_taxable = float(import_data.get('txval', 0))
            total_igst = float(import_data.get('iamt', 0))
            total_cgst = float(import_data.get('camt', 0))
            total_sgst = float(import_data.get('samt', 0))
            
            total_tax = total_igst + total_cgst + total_sgst
            total_value = total_taxable + total_tax
            
            return GSTTransaction(
                date=self._format_date(bill_date),
                party_name=f"Import-{port_code}",
                party_gstin="",
                party_state="Import",
                invoice_number=bill_num,
                invoice_date=bill_date,
                taxable_value=total_taxable,
                igst_amount=total_igst,
                cgst_amount=total_cgst,
                sgst_amount=total_sgst,
                total_tax=total_tax,
                invoice_value=total_value,
                is_interstate=True,  # Imports are always interstate
                transaction_type='purchase'
            )
            
        except Exception as e:
            logger.error(f"Error processing GSTR2B import transaction: {e}")
            return None

    def _process_gstr2b_isd_transaction(self, isd_data: Dict[str, Any]) -> Optional[GSTTransaction]:
        """Process ISD credit transaction from GSTR2B format."""
        try:
            isd_gstin = isd_data.get('isd_gstin', '')
            doc_num = isd_data.get('doc_num', '')
            doc_date = isd_data.get('doc_date', '')
            
            total_igst = float(isd_data.get('iamt', 0))
            total_cgst = float(isd_data.get('camt', 0))
            total_sgst = float(isd_data.get('samt', 0))
            
            total_tax = total_igst + total_cgst + total_sgst
            
            return GSTTransaction(
                date=self._format_date(doc_date),
                party_name=f"ISD-{isd_gstin[:10]}",
                party_gstin=isd_gstin,
                party_state=self._get_state_from_gstin(isd_gstin),
                invoice_number=doc_num,
                invoice_date=doc_date,
                taxable_value=0,  # ISD credits don't have taxable value
                igst_amount=total_igst,
                cgst_amount=total_cgst,
                sgst_amount=total_sgst,
                total_tax=total_tax,
                invoice_value=total_tax,
                is_interstate=total_igst > 0,
                transaction_type='purchase'
            )
            
        except Exception as e:
            logger.error(f"Error processing GSTR2B ISD transaction: {e}")
            return None

    def _process_gstr2a_b2b_invoice(self, invoice: Dict[str, Any], supplier_gstin: str, 
                                  supplier_state: str) -> Optional[GSTTransaction]:
        """Process a B2B invoice from GSTR2A format."""
        try:
            invoice_number = invoice.get('inum', '')
            invoice_date = invoice.get('idt', '')
            invoice_value = float(invoice.get('val', 0))
            
            # GSTR2A structure similar to GSTR1 for items
            total_taxable = 0
            total_igst = 0
            total_cgst = 0
            total_sgst = 0
            
            for item in invoice.get('itms', []):
                for itm_det in item.get('itm_det', []):
                    total_taxable += float(itm_det.get('txval', 0))
                    total_igst += float(itm_det.get('iamt', 0))
                    total_cgst += float(itm_det.get('camt', 0))
                    total_sgst += float(itm_det.get('samt', 0))
            
            total_tax = total_igst + total_cgst + total_sgst
            is_interstate = total_igst > 0 or supplier_state != self.company_state
            
            party_name = f"Supplier-{supplier_gstin[:10]}" if supplier_gstin else "Unknown Supplier"
            
            return GSTTransaction(
                date=self._format_date(invoice_date),
                party_name=party_name,
                party_gstin=supplier_gstin,
                party_state=supplier_state,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                taxable_value=total_taxable,
                igst_amount=total_igst,
                cgst_amount=total_cgst,
                sgst_amount=total_sgst,
                total_tax=total_tax,
                invoice_value=invoice_value,
                is_interstate=is_interstate,
                transaction_type='purchase'
            )
            
        except Exception as e:
            logger.error(f"Error processing GSTR2A B2B invoice: {e}")
            return None

    def _process_gstr2a_import_transaction(self, import_data: Dict[str, Any]) -> Optional[GSTTransaction]:
        """Process import transaction from GSTR2A format."""
        try:
            # Similar to GSTR2B but may have slightly different field names
            port_code = import_data.get('port_code', '')
            bill_num = import_data.get('bill_num', '')
            bill_date = import_data.get('bill_date', '')
            
            total_taxable = float(import_data.get('txval', 0))
            total_igst = float(import_data.get('iamt', 0))
            total_cgst = float(import_data.get('camt', 0))
            total_sgst = float(import_data.get('samt', 0))
            
            total_tax = total_igst + total_cgst + total_sgst
            total_value = total_taxable + total_tax
            
            return GSTTransaction(
                date=self._format_date(bill_date),
                party_name=f"Import-{port_code}",
                party_gstin="",
                party_state="Import",
                invoice_number=bill_num,
                invoice_date=bill_date,
                taxable_value=total_taxable,
                igst_amount=total_igst,
                cgst_amount=total_cgst,
                sgst_amount=total_sgst,
                total_tax=total_tax,
                invoice_value=total_value,
                is_interstate=True,
                transaction_type='purchase'
            )
            
        except Exception as e:
            logger.error(f"Error processing GSTR2A import transaction: {e}")
            return None

    def _process_b2b_invoice(self, invoice: Dict[str, Any], party_gstin: str, 
                           party_state: str, transaction_type: str) -> Optional[GSTTransaction]:
        """Process a B2B invoice and extract transaction data."""
        try:
            invoice_number = invoice.get('inum', '')
            invoice_date = invoice.get('idt', '')
            invoice_value = float(invoice.get('val', 0))
            
            # Process line items and calculate totals
            total_taxable = 0
            total_igst = 0
            total_cgst = 0
            total_sgst = 0
            
            for item in invoice.get('itms', []):
                for itm_det in item.get('itm_det', []):
                    total_taxable += float(itm_det.get('txval', 0))
                    total_igst += float(itm_det.get('iamt', 0))
                    total_cgst += float(itm_det.get('camt', 0))
                    total_sgst += float(itm_det.get('samt', 0))
            
            total_tax = total_igst + total_cgst + total_sgst
            is_interstate = total_igst > 0 or party_state != self.company_state
            
            # Generate party name from GSTIN if not available
            party_name = f"Party-{party_gstin[:10]}" if party_gstin else "Unknown Party"
            
            return GSTTransaction(
                date=self._format_date(invoice_date),
                party_name=party_name,
                party_gstin=party_gstin,
                party_state=party_state,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                taxable_value=total_taxable,
                igst_amount=total_igst,
                cgst_amount=total_cgst,
                sgst_amount=total_sgst,
                total_tax=total_tax,
                invoice_value=invoice_value,
                is_interstate=is_interstate,
                transaction_type=transaction_type
            )
            
        except Exception as e:
            logger.error(f"Error processing B2B invoice: {e}")
            return None
    
    def _process_b2cs_transaction(self, b2cs_data: Dict[str, Any], 
                                transaction_type: str) -> Optional[GSTTransaction]:
        """Process B2CS (small) transaction."""
        try:
            # B2CS doesn't have party details, so create generic entry
            party_state = b2cs_data.get('stin', self.company_state)  # State of supply
            total_taxable = float(b2cs_data.get('txval', 0))
            total_igst = float(b2cs_data.get('iamt', 0))
            total_cgst = float(b2cs_data.get('camt', 0))
            total_sgst = float(b2cs_data.get('samt', 0))
            
            total_tax = total_igst + total_cgst + total_sgst
            total_value = total_taxable + total_tax
            is_interstate = total_igst > 0 or party_state != self.company_state
            
            return GSTTransaction(
                date=datetime.now().strftime("%Y-%m-%d"),  # B2CS doesn't have specific dates
                party_name=f"B2CS-{party_state}",
                party_gstin="",
                party_state=party_state,
                invoice_number="B2CS-Consolidated",
                invoice_date="",
                taxable_value=total_taxable,
                igst_amount=total_igst,
                cgst_amount=total_cgst,
                sgst_amount=total_sgst,
                total_tax=total_tax,
                invoice_value=total_value,
                is_interstate=is_interstate,
                transaction_type=transaction_type
            )
            
        except Exception as e:
            logger.error(f"Error processing B2CS transaction: {e}")
            return None
    
    def _get_state_from_gstin(self, gstin: str) -> str:
        """Extract state from GSTIN."""
        if not gstin or len(gstin) < 2:
            return self.company_state
        
        state_code = gstin[:2]
        for state, code in self.state_codes.items():
            if code == state_code:
                return state
        
        return self.company_state
    
    def _format_date(self, date_str: str) -> str:
        """Format date to standard format."""
        if not date_str:
            return datetime.now().strftime("%Y-%m-%d")
        
        try:
            # GST dates are usually in DD-MM-YYYY format
            if len(date_str) >= 8:
                dt = datetime.strptime(date_str, "%d-%m-%Y")
                return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
        
        return date_str
    
    def generate_ledger_name(self, transaction: GSTTransaction, tax_type: str) -> str:
        """
        Generate descriptive ledger names for GST transactions.
        
        Args:
            transaction: GST transaction
            tax_type: Type of tax (IGST, CGST, SGST)
            
        Returns:
            Descriptive ledger name
        """
        # Determine prefix based on transaction type
        prefix = "Input" if transaction.transaction_type == "purchase" else "Output"
        
        # Calculate tax rate
        if transaction.taxable_value > 0:
            if tax_type == "IGST" and transaction.igst_amount > 0:
                rate = (transaction.igst_amount / transaction.taxable_value) * 100
                return f"{prefix} IGST {rate:.0f}%"
            elif tax_type == "CGST" and transaction.cgst_amount > 0:
                rate = (transaction.cgst_amount / transaction.taxable_value) * 100
                return f"{prefix} CGST {rate:.0f}%"
            elif tax_type == "SGST" and transaction.sgst_amount > 0:
                rate = (transaction.sgst_amount / transaction.taxable_value) * 100
                return f"{prefix} SGST {rate:.0f}%"
        
        # Fallback naming
        return f"{prefix} {tax_type}"
    
    def generate_main_ledger_name(self, transaction: GSTTransaction) -> str:
        """Generate main ledger name for the transaction."""
        transaction_type = "Purchase" if transaction.transaction_type == "purchase" else "Sales"
        location = "Interstate" if transaction.is_interstate else "Local"
        
        # Calculate overall tax rate
        if transaction.taxable_value > 0:
            total_rate = (transaction.total_tax / transaction.taxable_value) * 100
            return f"{location} {transaction_type} {total_rate:.0f}%"
        
        return f"{location} {transaction_type}"