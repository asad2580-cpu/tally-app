import streamlit as st
import json
import os
from PIL import Image
import io
from transaction_extractor import TransactionExtractor

# Set page configuration
st.set_page_config(
    page_title="Bank Statement Transaction Extractor",
    page_icon="🏦",
    layout="wide"
)

# Initialize the transaction extractor
@st.cache_resource
def get_extractor():
    return TransactionExtractor()

def main():
    st.title("🏦 Bank Statement Transaction Extractor")
    st.markdown("Upload bank statement images in PNG format to extract transaction data using AI")
    
    # Check if API key is available
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("⚠️ GEMINI_API_KEY environment variable not found. Please set your Gemini API key.")
        st.stop()
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a PNG bank statement image",
        type=['png'],
        help="Upload a clear image of your bank statement in PNG format"
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
                    
                    # Clear progress indicators
                    progress_bar.empty()
                    status_text.empty()
                    
                    if transactions:
                        st.success(f"🎉 Successfully extracted {len(transactions)} transactions!")
                        
                        # Display results
                        st.subheader("📋 Extracted Transactions")
                        
                        # Create tabs for different views
                        tab1, tab2, tab3 = st.tabs(["📊 Table View", "📄 JSON View", "💾 Download"])
                        
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
                            # Download options
                            st.subheader("💾 Download Options")
                            
                            # JSON download
                            json_str = json.dumps(transactions, indent=2)
                            st.download_button(
                                label="📄 Download as JSON",
                                data=json_str,
                                file_name="bank_transactions.json",
                                mime="application/json"
                            )
                            
                            # CSV download
                            if transactions:
                                import pandas as pd
                                df = pd.DataFrame(transactions)
                                csv = df.to_csv(index=False)
                                st.download_button(
                                    label="📊 Download as CSV",
                                    data=csv,
                                    file_name="bank_transactions.csv",
                                    mime="text/csv"
                                )
                    
                    else:
                        st.warning("⚠️ No transactions found in the image. Please ensure the image is clear and contains transaction data.")
                        
                except Exception as e:
                    st.error(f"❌ Error processing image: {str(e)}")
                    st.error("Please try again with a different image or check if the image is clear and readable.")

    # Instructions and tips
    with st.expander("📖 How to use this app"):
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

if __name__ == "__main__":
    main()
