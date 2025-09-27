import streamlit as st
import json
import os
from PIL import Image
import io
from transaction_extractor import TransactionExtractor
from tally_xml_generator import TallyXMLGenerator
from gst_processor import GSTProcessor

# Set page configuration
st.set_page_config(
    page_title="Tally ERP Automation Suite",
    page_icon="🏛️",
    layout="wide"
)

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
    col_config1, col_config2, col_config3 = st.columns(3)
    
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
    
    with col_config3:
        bank_ledger_name = st.text_input(
            "Bank Ledger Name", 
            placeholder="e.g., HDFC Bank, SBI Current Account",
            help="Name of the bank account ledger in your Tally (for bank statements)"
        )
    
    # Show configuration status
    config_status = []
    if company_name:
        config_status.append(f"Company: {company_name}")
    if company_state:
        config_status.append(f"State: {company_state}")
    if bank_ledger_name:
        config_status.append(f"Bank: {bank_ledger_name}")
    
    if config_status:
        st.success(f"✅ Configuration: {' | '.join(config_status)}")
    else:
        st.info("💡 Please configure company details above to proceed")
    
    st.divider()
    
    # Create tabs for different document types
    tab_bank, tab_invoice, tab_gst = st.tabs(["🏦 Bank Statements", "📄 Invoices", "📊 GST Returns"])
    
    with tab_bank:
        process_bank_statements(company_name, bank_ledger_name)
    
    with tab_invoice:
        process_invoices(company_name, company_state)
    
    with tab_gst:
        process_gst_returns(company_name, company_state)

def process_bank_statements(company_name: str, bank_ledger_name: str):
    """Handle bank statement processing."""
    st.subheader("🏦 Bank Statement Processing")
    st.markdown("Upload bank statement images (PNG) to extract transaction data and generate Tally XML")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a PNG bank statement image",
        type=['png'],
        help="Upload a clear image of your bank statement in PNG format",
        key="bank_statement_uploader"
    )
    
    if uploaded_file is not None:
        # Display uploaded image
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📄 Uploaded Image")
            try:
                image = Image.open(uploaded_file)
                st.image(image, caption="Bank Statement", use_column_width=True)
                
                # Image info
                st.info(f"**Image Details:**\n- Size: {image.size[0]} x {image.size[1]} pixels\n- Format: {image.format}\n- Mode: {image.mode}")
                
            except Exception as e:
                st.error(f"Error loading image: {str(e)}")
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
                        
                        # Convert image to bytes
                        img_bytes = io.BytesIO()
                        image.save(img_bytes, format='PNG')
                        img_bytes = img_bytes.getvalue()
                        
                        status_text.text("📊 Extracting transaction data...")
                        progress_bar.progress(75)
                        
                        # Extract transactions
                        transactions = extractor.extract_transactions(img_bytes)
                        
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
    
    # GST return type selection
    gst_return_type = st.selectbox(
        "GST Return Type",
        options=["GSTR2B", "GSTR2A", "GSTR1"],
        help="Select the type of GST return JSON file"
    )
    
    # File uploader for GST returns
    uploaded_files = st.file_uploader(
        "Choose GST return JSON files",
        type=['json'],
        accept_multiple_files=True,
        help="Upload JSON files downloaded from GST portal",
        key="gst_return_uploader"
    )
    
    if uploaded_files:
        st.success(f"📁 {len(uploaded_files)} JSON file(s) uploaded successfully!")
        
        # Initialize GST processor
        gst_processor = GSTProcessor(company_state)
        
        for uploaded_file in uploaded_files:
            with st.expander(f"📄 Processing: {uploaded_file.name}"):
                try:
                    # Read and parse JSON
                    json_data = json.load(uploaded_file)
                    
                    # Process based on return type
                    if gst_return_type == "GSTR2B":
                        transactions = gst_processor.process_gstr2b(json_data)
                        transaction_type_label = "Purchase Transactions"
                    elif gst_return_type == "GSTR1":
                        transactions = gst_processor.process_gstr1(json_data)
                        transaction_type_label = "Sales Transactions"
                    else:  # GSTR2A
                        st.info("GSTR2A processing similar to GSTR2B - using GSTR2B logic")
                        transactions = gst_processor.process_gstr2b(json_data)
                        transaction_type_label = "Purchase Transactions"
                    
                    if transactions:
                        st.success(f"✅ Extracted {len(transactions)} {transaction_type_label.lower()}")
                        
                        # Display summary
                        col1, col2, col3 = st.columns(3)
                        
                        total_value = sum(t.invoice_value for t in transactions)
                        total_tax = sum(t.total_tax for t in transactions)
                        interstate_count = sum(1 for t in transactions if t.is_interstate)
                        
                        with col1:
                            st.metric("Total Value", f"₹{total_value:,.2f}")
                        with col2:
                            st.metric("Total Tax", f"₹{total_tax:,.2f}")
                        with col3:
                            st.metric("Interstate Transactions", f"{interstate_count}/{len(transactions)}")
                        
                        # Show sample transactions
                        st.subheader("📋 Sample Transactions")
                        sample_data = []
                        for t in transactions[:10]:  # Show first 10
                            sample_data.append({
                                "Date": t.date,
                                "Party": t.party_name,
                                "State": t.party_state,
                                "Invoice": t.invoice_number,
                                "Value": f"₹{t.invoice_value:,.2f}",
                                "Tax": f"₹{t.total_tax:,.2f}",
                                "Type": "Interstate" if t.is_interstate else "Local"
                            })
                        
                        import pandas as pd
                        df = pd.DataFrame(sample_data)
                        st.dataframe(df, use_container_width=True)
                        
                        if len(transactions) > 10:
                            st.info(f"Showing first 10 of {len(transactions)} transactions")
                        
                        # Show ledger preview
                        st.subheader("🏷️ Ledger Name Preview")
                        ledger_preview = []
                        for t in transactions[:5]:  # Show first 5
                            main_ledger = gst_processor.generate_main_ledger_name(t)
                            tax_ledgers = []
                            
                            if t.igst_amount > 0:
                                tax_ledgers.append(gst_processor.generate_ledger_name(t, "IGST"))
                            if t.cgst_amount > 0:
                                tax_ledgers.append(gst_processor.generate_ledger_name(t, "CGST"))
                            if t.sgst_amount > 0:
                                tax_ledgers.append(gst_processor.generate_ledger_name(t, "SGST"))
                            
                            ledger_preview.append({
                                "Main Ledger": main_ledger,
                                "Tax Ledgers": ", ".join(tax_ledgers),
                                "Party": t.party_name
                            })
                        
                        df_ledgers = pd.DataFrame(ledger_preview)
                        st.dataframe(df_ledgers, use_container_width=True)
                        
                        # Store in session state for XML generation
                        st.session_state[f'gst_transactions_{uploaded_file.name}'] = transactions
                        st.session_state[f'gst_processor'] = gst_processor
                        
                        st.info("💡 XML generation and masters import will be available in the next update!")
                        
                    else:
                        st.warning("⚠️ No transactions found in this file")
                        
                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON file: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Error processing file: {str(e)}")
    
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
