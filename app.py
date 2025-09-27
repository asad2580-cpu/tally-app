import streamlit as st
import json
import os
from PIL import Image
import io
from pdf2image import convert_from_bytes
from transaction_extractor import TransactionExtractor
from tally_xml_generator import TallyXMLGenerator
from gst_processor import GSTProcessor

# Set page configuration
st.set_page_config(
    page_title="Tally ERP Automation Suite",
    page_icon="🏛️",
    layout="wide"
)

def convert_file_to_png_bytes(uploaded_file) -> bytes:
    """
    Convert uploaded file (PNG, JPG, JPEG, PDF) to PNG bytes.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        PNG image bytes
    """
    file_bytes = uploaded_file.read()
    file_extension = uploaded_file.name.lower().split('.')[-1]
    
    try:
        if file_extension == 'pdf':
            # Convert PDF to images (take first page)
            images = convert_from_bytes(file_bytes, first_page=1, last_page=1, dpi=200)
            if images:
                # Convert PIL Image to PNG bytes
                img_bytes = io.BytesIO()
                images[0].save(img_bytes, format='PNG')
                return img_bytes.getvalue()
            else:
                raise ValueError("No images found in PDF")
        
        elif file_extension in ['jpg', 'jpeg']:
            # Convert JPG/JPEG to PNG
            image = Image.open(io.BytesIO(file_bytes))
            # Convert to RGB if needed (JPEG can be in different modes)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            return img_bytes.getvalue()
        
        elif file_extension == 'png':
            # Already PNG, return as-is
            return file_bytes
        
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
            
    except Exception as e:
        raise Exception(f"Error converting {file_extension.upper()} file: {str(e)}")

# Initialize the transaction extractor
@st.cache_resource
def get_extractor():
    return TransactionExtractor()

def main():
    st.title("🏛️ Tally ERP Automation Suite")
    st.markdown("Comprehensive automation solution for importing bank statements, invoices, and GST returns into Tally")
    
    # Check if API key is available
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("⚠️ GEMINI_API_KEY environment variable not found. Please set your Gemini API key.")
        st.stop()
    
    # Global Configuration Section
    st.subheader("⚙️ Company Configuration")
    col_config1, col_config2 = st.columns(2)
    
    with col_config1:
        company_name = st.text_input(
            "Company Name (as in Tally)",
            placeholder="Enter your company name exactly as it appears in Tally",
            help="This should match your company name in Tally exactly"
        )
    
    with col_config2:
        company_state = st.selectbox(
            "Company State",
            options=[
                "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
                "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
                "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
                "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Puducherry"
            ],
            index=None,
            placeholder="Select your company's state",
            help="Required for accurate GST bifurcation (CGST+SGST vs IGST)"
        )
    
    # Show configuration status
    config_status = []
    if company_name:
        config_status.append(f"Company: {company_name}")
    if company_state:
        config_status.append(f"State: {company_state}")
    
    if config_status:
        st.success(f"✅ Configuration: {' | '.join(config_status)}")
    else:
        st.info("💡 Please configure company details above to proceed")
    
    st.divider()
    
    # Create tabs for different document types
    tab_bank, tab_invoice, tab_gst = st.tabs(["🏦 Bank Statements", "📄 Invoices", "📊 GST Returns"])
    
    with tab_bank:
        process_bank_statements(company_name)
    
    with tab_invoice:
        process_invoices(company_name, company_state)
    
    with tab_gst:
        process_gst_returns(company_name, company_state)

def process_bank_statements(company_name: str):
    """Handle bank statement processing."""
    st.subheader("🏦 Bank Statement Processing")
    st.markdown("Upload bank statement images/PDFs to extract transaction data and generate Tally XML")
    
    # Bank Account Configuration
    st.subheader("💰 Bank Account Configuration")
    bank_ledger_name = st.text_input(
        "Bank Ledger Name", 
        placeholder="e.g., HDFC Bank, SBI Current Account",
        help="Name of the bank account ledger in your Tally (required for XML generation)",
        key="bank_ledger_input"
    )
    
    if bank_ledger_name:
        st.success(f"✅ Bank Account: {bank_ledger_name}")
    else:
        st.info("💡 Please enter your bank ledger name to proceed with Tally XML generation")
    
    st.divider()
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a bank statement file",
        type=['png', 'jpg', 'jpeg', 'pdf'],
        help="Upload a clear image or PDF of your bank statement (PNG, JPG, JPEG, PDF formats supported)",
        key="bank_statement_uploader"
    )
    
    if uploaded_file is not None:
        # Convert file to PNG format for processing
        try:
            png_bytes = convert_file_to_png_bytes(uploaded_file)
            original_format = uploaded_file.name.lower().split('.')[-1].upper()
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            return
        
        # Display uploaded file
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader(f"📄 Uploaded {original_format} File")
            try:
                # Display the converted PNG image
                display_image = Image.open(io.BytesIO(png_bytes))
                st.image(display_image, caption=f"Bank Statement ({original_format})", use_column_width=True)
                
                # File info
                st.info(f"**File Details:**\n- Original Format: {original_format}\n- Size: {display_image.size[0]} x {display_image.size[1]} pixels\n- Processed Format: PNG\n- Mode: {display_image.mode}")
                
            except Exception as e:
                st.error(f"Error displaying image: {str(e)}")
                return
        
        with col2:
            st.subheader("🔄 Transaction Extraction")
            
            # Check if transactions are already extracted
            if 'extracted_transactions' in st.session_state and st.session_state.get('extraction_completed', False):
                st.success(f"✅ {len(st.session_state['extracted_transactions'])} transactions already extracted!")
                if st.button("🔄 Re-extract Transactions", type="secondary"):
                    # Clear existing data and re-extract
                    if 'extracted_transactions' in st.session_state:
                        del st.session_state['extracted_transactions']
                    if 'extraction_completed' in st.session_state:
                        del st.session_state['extraction_completed']
                    if 'tally_xml' in st.session_state:
                        del st.session_state['tally_xml']
                    st.rerun()
            else:
                if st.button("Extract Transactions", type="primary"):
                    try:
                        # Show progress
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        status_text.text("🔍 Analyzing image...")
                        progress_bar.progress(25)
                        
                        # Get extractor
                        extractor = get_extractor()
                        
                        status_text.text("🤖 Processing with AI...")
                        progress_bar.progress(50)
                        
                        status_text.text("📊 Extracting transaction data...")
                        progress_bar.progress(75)
                        
                        # Extract transactions using already converted PNG bytes
                        transactions = extractor.extract_transactions(png_bytes)
                        
                        status_text.text("✅ Complete!")
                        progress_bar.progress(100)
                        
                        # Store transactions in session state for persistence
                        st.session_state['extracted_transactions'] = transactions
                        st.session_state['extraction_completed'] = True
                        
                        # Clear progress indicators
                        progress_bar.empty()
                        status_text.empty()
                        
                        if transactions:
                            st.success(f"🎉 Successfully extracted {len(transactions)} transactions!")
                        else:
                            st.warning("⚠️ No transactions found in the image. Please ensure the image is clear and contains transaction data.")
                            
                    except Exception as e:
                        st.error(f"❌ Error processing image: {str(e)}")
                        st.error("Please try again with a different image or check if the image is clear and readable.")
        
        # Display extracted transactions if available
        if 'extracted_transactions' in st.session_state and st.session_state.get('extraction_completed', False):
            transactions = st.session_state['extracted_transactions']
            
            if transactions:
                st.divider()
                st.subheader("📋 Extracted Transactions")
                
                # Create tabs for different views
                tab1, tab2, tab3, tab4 = st.tabs(["📊 Table View", "📄 JSON View", "🔄 Tally XML", "💾 Download"])
                
                with tab1:
                    # Display as dataframe
                    import pandas as pd
                    df = pd.DataFrame(transactions)
                    st.dataframe(df, use_container_width=True)
                            
                    # Summary statistics
                    if len(transactions) > 0:
                        st.subheader("📈 Summary")
                        col_a, col_b, col_c = st.columns(3)
                        
                        total_debits = sum(float(t.get('debit_amount', 0) or 0) for t in transactions)
                        total_credits = sum(float(t.get('credit_amount', 0) or 0) for t in transactions)
                        
                        with col_a:
                            st.metric("Total Transactions", len(transactions))
                        with col_b:
                            st.metric("Total Debits", f"₹{total_debits:,.2f}")
                        with col_c:
                            st.metric("Total Credits", f"₹{total_credits:,.2f}")
                        
                        with tab2:
                            # Display as JSON
                            json_str = json.dumps(transactions, indent=2)
                            st.code(json_str, language="json")
                        
                        with tab3:
                            # Tally XML Generation
                            if company_name and bank_ledger_name:
                                st.subheader("🔄 Generate Tally XML")
                                
                                try:
                                    # Initialize XML generator
                                    xml_generator = TallyXMLGenerator(company_name, bank_ledger_name)
                                    
                                    # Validate data before generation
                                    validation_result = xml_generator.validate_xml_structure(transactions)
                                    
                                    # Show validation results
                                    if validation_result['valid']:
                                        st.success(f"✅ Ready to generate XML for {validation_result['transaction_count']} transactions")
                                        
                                        if validation_result['warnings']:
                                            with st.expander("⚠️ Validation Warnings"):
                                                for warning in validation_result['warnings']:
                                                    st.warning(warning)
                                        
                                        # Generate XML button
                                        if st.button("🔄 Generate Tally XML", type="primary"):
                                            with st.spinner("Generating Tally XML..."):
                                                xml_content = xml_generator.generate_xml(transactions)
                                                
                                                st.success("✅ Tally XML generated successfully!")
                                                
                                                # Display XML preview (first 2000 chars)
                                                st.subheader("📄 XML Preview")
                                                preview_xml = xml_content[:2000]
                                                if len(xml_content) > 2000:
                                                    preview_xml += "\n... (truncated, full XML available in download)"
                                                
                                                st.code(preview_xml, language="xml")
                                                
                                                # Store XML in session state for download
                                                st.session_state['tally_xml'] = xml_content
                                                
                                                # Quick info about the XML
                                                st.info(f"""
                                                **XML Details:**
                                                - Company: {company_name}
                                                - Bank Ledger: {bank_ledger_name}
                                                - Suspense Ledger: Suspense (auto-created if needed)
                                                - Transactions: {len(transactions)}
                                                - XML Size: {len(xml_content)} characters
                                                """)
                                    else:
                                        st.error("❌ Validation failed. Please fix the following errors:")
                                        for error in validation_result['errors']:
                                            st.error(f"• {error}")
                                        
                                        if validation_result['warnings']:
                                            st.warning("Additional warnings:")
                                            for warning in validation_result['warnings']:
                                                st.warning(f"• {warning}")
                                                
                                except Exception as e:
                                    st.error(f"❌ Error generating XML: {str(e)}")
                            else:
                                st.warning("⚠️ Please configure company name and bank ledger name in the settings above to generate Tally XML")
                        
                        with tab4:
                            # Download options
                            st.subheader("💾 Download Options")
                            
                            col_dl1, col_dl2, col_dl3 = st.columns(3)
                            
                            with col_dl1:
                                # JSON download
                                json_str = json.dumps(transactions, indent=2)
                                st.download_button(
                                    label="📄 Download JSON",
                                    data=json_str,
                                    file_name="bank_transactions.json",
                                    mime="application/json"
                                )
                            
                            with col_dl2:
                                # CSV download
                                if transactions:
                                    import pandas as pd
                                    df = pd.DataFrame(transactions)
                                    csv = df.to_csv(index=False)
                                    st.download_button(
                                        label="📊 Download CSV",
                                        data=csv,
                                        file_name="bank_transactions.csv",
                                        mime="text/csv"
                                    )
                            
                            with col_dl3:
                                # Tally XML download
                                if 'tally_xml' in st.session_state:
                                    st.download_button(
                                        label="🔄 Download Tally XML",
                                        data=st.session_state['tally_xml'],
                                        file_name="tally_import.xml",
                                        mime="application/xml"
                                    )
                                else:
                                    st.info("Generate XML first in Tally XML tab")
                            
                            # Instructions for XML import
                            if 'tally_xml' in st.session_state:
                                st.divider()
                                with st.expander("📖 How to import XML into Tally"):
                                    st.markdown("""
                                    ### Steps to import into Tally:
                                    
                                    1. **Open Tally** and select your company
                                    2. **Go to Gateway of Tally** → Import → XML Files
                                    3. **Browse and select** the downloaded XML file
                                    4. **Click Import** to process the transactions
                                    5. **Verify** the imported transactions in your vouchers
                                    
                                    ### Important Notes:
                                    - 🏢 Make sure the company name matches exactly
                                    - 💰 All transactions will be posted to "Suspense" ledger
                                    - ✅ The Suspense ledger will be created automatically if it doesn't exist
                                    - 📝 You can later transfer amounts from Suspense to proper ledgers
                                    - 🔄 Always backup your Tally data before importing
                                    
                                    ### After Import:
                                    - Review transactions in Receipt/Payment vouchers
                                    - Move amounts from Suspense to appropriate ledgers
                                    - Verify running balance matches your bank statement
                                    """)

    # Instructions and tips for bank statements
    with st.expander("📖 How to use Bank Statement Processing"):
        st.markdown("""
        ### Instructions:
        1. **Upload Image**: Select a PNG image of your bank statement
        2. **Extract Data**: Click the "Extract Transactions" button
        3. **Review Results**: Check the extracted transaction data
        4. **Download**: Save the results as JSON or CSV
        
        ### Tips for better results:
        - ✅ Use high-quality, clear images
        - ✅ Ensure good lighting and contrast
        - ✅ Make sure all text is readable
        - ✅ Avoid blurry or rotated images
        - ✅ Include the complete transaction table
        
        ### Supported Data Fields:
        - **Date**: Transaction date
        - **Narration**: Transaction description
        - **Debit Amount**: Money debited from account
        - **Credit Amount**: Money credited to account  
        - **Running Balance**: Account balance after transaction
        """)

def process_invoices(company_name: str, company_state: str | None):
    """Handle invoice processing."""
    st.subheader("📄 Invoice Processing")
    st.markdown("Upload invoice images (PNG/PDF) to extract transaction data and generate purchase/sales vouchers")
    
    if not company_name or not company_state:
        st.warning("⚠️ Please configure company name and state in the settings above")
        return
    
    # Invoice type selection
    invoice_type = st.selectbox(
        "Invoice Type",
        options=["Purchase Invoice", "Sales Invoice"],
        help="Select whether this is a purchase or sales invoice"
    )
    
    # File uploader for invoices
    uploaded_files = st.file_uploader(
        "Choose invoice files",
        type=['png', 'jpg', 'jpeg', 'pdf'],
        accept_multiple_files=True,
        help="Upload clear images or PDFs of your invoices",
        key="invoice_uploader"
    )
    
    if uploaded_files:
        st.info(f"📁 {len(uploaded_files)} file(s) uploaded. Processing will be available soon.")
        
        # Placeholder for invoice processing
        with st.expander("🔮 Coming Soon - Invoice Processing Features"):
            st.markdown("""
            **Planned Features:**
            - 🔍 AI-powered invoice data extraction
            - 📊 Automatic GST calculation and bifurcation
            - 🏢 Vendor/customer master creation
            - 📦 Item master management
            - 💰 Accurate debit/credit mapping
            - 🔄 Purchase/Sales voucher XML generation
            - 📝 Descriptive ledger naming (Local Purchase 18%, Input IGST 18%, etc.)
            """)
    
    # Instructions
    with st.expander("📖 How to use Invoice Processing"):
        st.markdown("""
        ### Coming Soon:
        - Support for both purchase and sales invoices
        - Automatic GST bifurcation based on company state
        - Smart ledger creation with descriptive names
        - Masters import XML for new vendors/customers/items
        """)

def process_gst_returns(company_name: str, company_state: str | None):
    """Handle GST return JSON processing."""
    st.subheader("📊 GST Return Processing")
    st.markdown("Upload GST return JSON files (GSTR2B/2A/R1) to import bulk transactions into Tally")
    
    if not company_name or not company_state:
        st.warning("⚠️ Please configure company name and state in the settings above")
        return
    
    # GST return type selection with separate sections
    st.markdown("### 📥 Upload GST Return Files")
    st.markdown("Choose the appropriate GST return type and upload your JSON file:")
    
    # Create separate tabs for each GST return type
    tab_gstr1, tab_gstr2a, tab_gstr2b = st.tabs(["📤 GSTR1 (Sales)", "📥 GSTR2A (Purchase - Auto)", "📊 GSTR2B (Purchase - Static)"])
    
    with tab_gstr1:
        st.markdown("**GSTR1**: Outward supplies (Sales) - Upload JSON downloaded from GST portal")
        gstr1_files = st.file_uploader(
            "Choose GSTR1 JSON files",
            type=['json'],
            accept_multiple_files=True,
            help="Upload GSTR1 JSON files downloaded from GST portal (Outward supplies)",
            key="gstr1_uploader"
        )
        if gstr1_files:
            process_gst_files(gstr1_files, "GSTR1", company_state)
    
    with tab_gstr2a:
        st.markdown("**GSTR2A**: Auto-drafted inward supplies (Purchase) - Upload JSON downloaded from GST portal")
        gstr2a_files = st.file_uploader(
            "Choose GSTR2A JSON files",
            type=['json'],
            accept_multiple_files=True,
            help="Upload GSTR2A JSON files downloaded from GST portal (Auto-drafted inward supplies)",
            key="gstr2a_uploader"
        )
        if gstr2a_files:
            process_gst_files(gstr2a_files, "GSTR2A", company_state)
    
    with tab_gstr2b:
        st.markdown("**GSTR2B**: Static ITC statement (Purchase) - Upload JSON downloaded from GST portal")
        gstr2b_files = st.file_uploader(
            "Choose GSTR2B JSON files",
            type=['json'],
            accept_multiple_files=True,
            help="Upload GSTR2B JSON files downloaded from GST portal (Static ITC statement)",
            key="gstr2b_uploader"
        )
        if gstr2b_files:
            process_gst_files(gstr2b_files, "GSTR2B", company_state)

def process_gst_files(uploaded_files, gst_return_type, company_state):
    """Process GST return files based on type."""
    st.success(f"📁 {len(uploaded_files)} {gst_return_type} file(s) uploaded successfully!")
    
    # Initialize GST processor
    gst_processor = GSTProcessor(company_state)
    
    for uploaded_file in uploaded_files:
        with st.expander(f"📄 Processing: {uploaded_file.name}"):
            try:
                # Read and parse JSON
                json_data = json.load(uploaded_file)
                
                # Process based on return type using updated methods
                if gst_return_type == "GSTR1":
                    transactions = gst_processor.process_gstr1(json_data)
                    transaction_type_label = "Sales Transactions"
                elif gst_return_type == "GSTR2A":
                    transactions = gst_processor.process_gstr2a(json_data)
                    transaction_type_label = "Purchase Transactions (Auto-drafted)"
                elif gst_return_type == "GSTR2B":
                    transactions = gst_processor.process_gstr2b(json_data)
                    transaction_type_label = "Purchase Transactions (Static ITC)"
                else:
                    st.error(f"Unsupported GST return type: {gst_return_type}")
                    continue
                
                if transactions:
                    st.success(f"✅ Extracted {len(transactions)} {transaction_type_label.lower()}")
                    
                    # Display summary
                    col1, col2, col3 = st.columns(3)
                    
                    total_value = sum(t.invoice_value for t in transactions)
                    total_tax = sum(t.total_tax for t in transactions)
                    interstate_count = sum(1 for t in transactions if t.is_interstate)
                    
                    with col1:
                        st.metric("Total Transactions", len(transactions))
                    with col2:
                        st.metric("Total Value", f"₹{total_value:,.2f}")
                    with col3:
                        st.metric("Interstate Transactions", interstate_count)
                    
                    # Display transaction details in a table
                    if len(transactions) > 0:
                        import pandas as pd
                        df_data = []
                        for t in transactions:
                            df_data.append({
                                'Date': t.date,
                                'Party': t.party_name,
                                'Invoice No': t.invoice_number,
                                'Taxable Value': f"₹{t.taxable_value:,.2f}",
                                'IGST': f"₹{t.igst_amount:,.2f}",
                                'CGST': f"₹{t.cgst_amount:,.2f}",
                                'SGST': f"₹{t.sgst_amount:,.2f}",
                                'Total Tax': f"₹{t.total_tax:,.2f}",
                                'Invoice Value': f"₹{t.invoice_value:,.2f}",
                                'Interstate': '✓' if t.is_interstate else '✗'
                            })
                        
                        df = pd.DataFrame(df_data)
                        st.dataframe(df, use_container_width=True)
                        
                        # Download option
                        csv = df.to_csv(index=False)
                        st.download_button(
                            label=f"📊 Download {gst_return_type} Data as CSV",
                            data=csv,
                            file_name=f"{gst_return_type}_{uploaded_file.name.replace('.json', '')}.csv",
                            mime="text/csv"
                        )
                else:
                    st.warning(f"⚠️ No transactions found in {gst_return_type} file")
                    
            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON file: {str(e)}")
            except Exception as e:
                st.error(f"❌ Error processing {gst_return_type} file: {str(e)}")
    
    # GST Portal Offline JSON Generator
    st.divider()
    st.markdown("### 🔧 GST Portal Offline Utility")
    st.markdown("Create JSON files for uploading to GST portal (offline utility tool)")
    
    with st.expander("📤 Generate GSTR1 JSON for GST Portal Upload"):
        st.markdown("**Create GSTR1 JSON file for outward supplies to upload on GST portal**")
        
        # Invoice entry form
        st.subheader("Invoice Details Entry")
        col1, col2 = st.columns(2)
        
        with col1:
            customer_gstin = st.text_input("Customer GSTIN", placeholder="01ABCDE1234F1Z5")
            invoice_number = st.text_input("Invoice Number", placeholder="INV001")
            invoice_date = st.date_input("Invoice Date")
        
        with col2:
            place_of_supply = st.selectbox("Place of Supply", 
                options=["01-Jammu and Kashmir", "02-Himachal Pradesh", "03-Punjab", "04-Chandigarh", 
                        "05-Uttarakhand", "06-Haryana", "07-Delhi", "08-Rajasthan", "09-Uttar Pradesh",
                        "10-Bihar", "11-Sikkim", "12-Arunachal Pradesh", "13-Nagaland", "14-Manipur",
                        "15-Mizoram", "16-Tripura", "17-Meghalaya", "18-Assam", "19-West Bengal",
                        "20-Jharkhand", "21-Odisha", "22-Chhattisgarh", "23-Madhya Pradesh",
                        "24-Gujarat", "25-Daman and Diu", "26-Dadra and Nagar Haveli", "27-Maharashtra",
                        "28-Andhra Pradesh", "29-Karnataka", "30-Goa", "31-Lakshadweep", "32-Kerala",
                        "33-Tamil Nadu", "34-Puducherry", "35-Andaman and Nicobar Islands", "36-Telangana",
                        "37-Andhra Pradesh"],
                help="Select place of supply for the transaction")
            
            tax_rate = st.selectbox("Tax Rate (%)", options=[0, 5, 12, 18, 28])
            taxable_value = st.number_input("Taxable Value (₹)", min_value=0.0, format="%.2f")
        
        if st.button("Add to GSTR1 JSON", type="primary"):
            if customer_gstin and invoice_number and taxable_value > 0:
                # Create GSTR1 JSON structure
                pos_code = place_of_supply.split('-')[0]
                gst_processor = GSTProcessor(company_state)
                company_state_code = next((code for state, code in gst_processor.state_codes.items() if state == company_state), "27")
                
                # Calculate tax amounts
                is_interstate = pos_code != company_state_code
                if is_interstate:
                    igst_amount = (taxable_value * tax_rate) / 100
                    cgst_amount = 0
                    sgst_amount = 0
                else:
                    igst_amount = 0
                    cgst_amount = (taxable_value * tax_rate) / 200  # Half of total tax
                    sgst_amount = (taxable_value * tax_rate) / 200  # Half of total tax
                
                total_value = taxable_value + igst_amount + cgst_amount + sgst_amount
                
                gstr1_json = {
                    "version": "GST1.1",
                    "hash": "auto_generated_hash",
                    "gstin": f"{company_state_code}ABCDE1234F1Z5",  # Placeholder GSTIN
                    "fp": invoice_date.strftime("%m%Y"),
                    "b2b": [
                        {
                            "ctin": customer_gstin,
                            "inv": [
                                {
                                    "inum": invoice_number,
                                    "idt": invoice_date.strftime("%d-%m-%Y"),
                                    "val": round(total_value, 2),
                                    "pos": pos_code,
                                    "rchrg": "N",
                                    "etin": "",
                                    "inv_typ": "R",
                                    "itms": [
                                        {
                                            "num": 1,
                                            "itm_det": {
                                                "rt": tax_rate,
                                                "txval": round(taxable_value, 2),
                                                "iamt": round(igst_amount, 2),
                                                "camt": round(cgst_amount, 2),
                                                "samt": round(sgst_amount, 2),
                                                "csamt": 0
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    ],
                    "b2cs": [],
                    "hsn": [],
                    "doc_issue": {}
                }
                
                st.success("✅ GSTR1 JSON created successfully!")
                
                # Display JSON preview
                st.subheader("📄 Generated JSON Preview")
                st.code(json.dumps(gstr1_json, indent=2), language="json")
                
                # Download button
                json_str = json.dumps(gstr1_json, indent=2)
                st.download_button(
                    label="📥 Download GSTR1 JSON for GST Portal",
                    data=json_str,
                    file_name=f"GSTR1_{invoice_date.strftime('%m%Y')}_{invoice_number}.json",
                    mime="application/json"
                )
                
                st.info("""
                **How to use this JSON file:**
                1. Download the JSON file
                2. Login to GST Portal → Returns Dashboard
                3. Select GSTR-1 → Upload JSON File
                4. Browse and select this downloaded file
                5. Review and submit your return
                """)
            else:
                st.error("⚠️ Please fill all required fields with valid data")
    
    # Instructions
    with st.expander("📖 How to use GST Return Processing"):
        st.markdown("""
        ### Features:
        - ⚡ **Ultra-fast processing**: JSON parsing in milliseconds
        - 📊 **Bulk transactions**: Process hundreds of transactions at once
        - 🧠 **Smart ledger naming**: "Input IGST 18%", "Local Purchase 28%"
        - 🏢 **Auto party creation**: Extract vendor/customer from GSTIN
        - 🗺️ **State-based logic**: Automatic CGST+SGST vs IGST determination
        
        ### How to use:
        1. Download JSON files from GST portal (GSTR2B/1/2A)
        2. Select the correct return type above
        3. Upload the JSON files
        4. Review the extracted transactions and ledger names
        5. XML generation coming soon!
        
        ### Supported Returns:
        - **GSTR2B**: Purchase transactions with input tax credit
        - **GSTR1**: Sales transactions with output tax
        - **GSTR2A**: Purchase transactions (auto-matched)
        """)

if __name__ == "__main__":
    main()
