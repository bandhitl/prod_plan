import streamlit as st
import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go
import json

# Try to import openai, handle if not installed
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None  # Set to None to prevent undefined variable errors
    st.warning("⚠️ OpenAI library not installed - AI Analysis will not be available")

# --- Configuration and Constants ---
HISTORICAL_REQUIRED_COLS = ["BRANDPRODUCT", "Item Code", "TON", "Item Name"]

# Check if we have API key from environment or secrets
OPENAI_API_KEY = None
try:
    import os
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        # Try Streamlit secrets
        try:
            OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")
        except:
            pass
except:
    pass

# --- File Processing Functions ---
def process_historical_file(uploaded_file):
    """
    Processes the uploaded historical data Excel file.
    Expected structure: Row 1 = title, Row 2 = headers, Row 3+ = data
    """
    try:
        # Try different header positions
        header_positions = [0, 1, 2]
        df = None
        
        for header_pos in header_positions:
            try:
                temp_df = pd.read_excel(uploaded_file, header=header_pos)
                # Check if required columns exist
                cols_found = sum(1 for col in HISTORICAL_REQUIRED_COLS 
                               if any(req_col.upper() in str(temp_col).upper() 
                                     for temp_col in temp_df.columns 
                                     for req_col in [col]))
                
                if cols_found >= 3:  # Need at least 3 out of 4 required columns
                    df = temp_df
                    st.success(f"✅ Found valid headers at row {header_pos + 1}")
                    break
            except:
                continue
        
        if df is None:
            st.error("❌ Could not find valid headers in the file")
            return None
        
        # Map columns to standard names
        column_mapping = {}
        for req_col in HISTORICAL_REQUIRED_COLS:
            for df_col in df.columns:
                if req_col.upper() in str(df_col).upper():
                    column_mapping[df_col] = req_col
                    break
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Check required columns
        missing_cols = [col for col in HISTORICAL_REQUIRED_COLS if col not in df.columns]
        if missing_cols:
            st.error(f"Missing required columns: {', '.join(missing_cols)}")
            return None
        
        # Clean and validate data
        original_count = len(df)
        df['TON'] = pd.to_numeric(df['TON'], errors='coerce')
        df = df.dropna(subset=['TON'])
        df = df[df['TON'] > 0]  # Only positive TON values
        df = df.dropna(subset=['BRANDPRODUCT', 'Item Code'])
        
        # Remove empty strings
        df = df[df['BRANDPRODUCT'].astype(str).str.strip() != '']
        df = df[df['Item Code'].astype(str).str.strip() != '']
        
        st.write(f"📊 **Data Summary:**")
        st.write(f"- Total rows: {original_count:,}")
        st.write(f"- Valid records: {len(df):,}")
        st.write(f"- Columns: {list(df.columns)}")
        
        # Brand summary
        brand_summary = df.groupby('BRANDPRODUCT').agg({
            'Item Code': 'nunique',
            'TON': ['count', 'sum']
        }).round(2)
        brand_summary.columns = ['Unique SKUs', 'Records', 'Total TON']
        brand_summary = brand_summary.sort_values('Total TON', ascending=False)
        
        st.write("**📈 Brand Summary:**")
        st.dataframe(brand_summary, use_container_width=True)
        
        return df
        
    except Exception as e:
        st.error(f"Error processing historical file: {e}")
        import traceback
        st.error(f"Details: {traceback.format_exc()}")
        return None

def process_target_file(uploaded_file):
    """
    Processes the BNI Sales Rolling target file with the specific structure.
    """
    try:
        # Read file without header specification
        df = pd.read_excel(uploaded_file, sheet_name=0, header=None)
        
        st.write("🔍 **BNI Sales Rolling File Preview:**")
        st.dataframe(df.head(10))
        
        # Check file structure
        if len(df) < 3:
            st.error("❌ File has insufficient data - needs at least 3 rows")
            return None
        
        # Find May and W1 columns
        may_col_idx = None
        w1_col_idx = None
        
        # Search in first 3 rows
        for row_idx in range(min(3, len(df))):
            for col_idx in range(len(df.columns)):
                cell_value = str(df.iloc[row_idx, col_idx]).strip().lower()
                if 'may' in cell_value and may_col_idx is None:
                    may_col_idx = col_idx
                    st.success(f"✅ Found 'May' column at position ({row_idx+1}, {col_idx+1})")
                elif 'w1' in cell_value and w1_col_idx is None:
                    w1_col_idx = col_idx
                    st.success(f"✅ Found 'W1' column at position ({row_idx+1}, {col_idx+1})")
        
        # Use defaults if not found
        if may_col_idx is None:
            may_col_idx = 1
            st.warning(f"⚠️ 'May' column not found, using default column 2")
        
        if w1_col_idx is None:
            w1_col_idx = 2
            st.warning(f"⚠️ 'W1' column not found, using default column 3")
        
        # Find data start and end rows
        start_row_idx = 2
        end_row_idx = len(df)
        
        for i in range(start_row_idx, len(df)):
            if i < len(df):
                cell_value = str(df.iloc[i, 0]).strip().lower()
                if 'total' in cell_value:
                    end_row_idx = i
                    st.info(f"📍 Found 'Total' row at row {i+1}")
                    break
        
        # Extract category data
        category_data = []
        for i in range(start_row_idx, end_row_idx):
            if i < len(df):
                category_name = df.iloc[i, 0]
                may_value = df.iloc[i, may_col_idx] if may_col_idx < len(df.columns) else 0
                w1_value = df.iloc[i, w1_col_idx] if w1_col_idx < len(df.columns) else 0
                
                # Clean data
                if pd.notna(category_name) and str(category_name).strip() != '':
                    try:
                        may_value = float(str(may_value).strip()) if pd.notna(may_value) else 0
                    except:
                        may_value = 0
                    
                    try:
                        w1_value = float(str(w1_value).strip()) if pd.notna(w1_value) else 0
                    except:
                        w1_value = 0
                    
                    category_data.append({
                        'Category': str(category_name).strip(),
                        'MayTarget': may_value,
                        'W1Target': w1_value
                    })
        
        # Show extracted data
        if category_data:
            st.write(f"📋 **Extracted Data ({len(category_data)} categories):**")
            preview_df = pd.DataFrame(category_data)
            st.dataframe(preview_df)
            
            # Convert to dictionary format
            category_targets = {}
            for item in category_data:
                category_targets[item['Category']] = {
                    'mayTarget': item['MayTarget'],
                    'w1Target': item['W1Target']
                }
            
            st.success(f"✅ Processing successful! Found {len(category_targets)} categories")
            return category_targets
        else:
            st.error("❌ No category data found in file")
            return None
            
    except Exception as e:
        st.error(f"Error processing target file: {e}")
        import traceback
        st.error(f"Details: {traceback.format_exc()}")
        return None

def map_categories_to_historical_brands(category_targets, historical_df):
    """Maps BNI categories to historical brands and aggregates targets."""
    
    # Create historical summary
    historical_summary = {}
    if historical_df is not None and not historical_df.empty:
        try:
            hist_summary = historical_df.groupby('BRANDPRODUCT')['TON'].sum()
            historical_summary = hist_summary.to_dict()
        except Exception as e:
            st.error(f"Error creating historical summary: {e}")
            historical_summary = {}
    
    brand_mapping = {}
    brand_targets_agg = {}
    
    if not category_targets:
        st.error("❌ No category targets data")
        return {}, {}
    
    processed_count = 0
    skipped_count = 0
    
    for category, targets in category_targets.items():
        matching_brand = None
        cat_lower = str(category).lower().strip()
        
        # Check MFG first, then determine product type
        if 'mfg' not in cat_lower:
            skipped_count += 1
            continue  # Skip non-MFG items
        
        # Determine brand based on category name
        if 'scg' in cat_lower:
            if 'pipe' in cat_lower or 'conduit' in cat_lower:
                matching_brand = 'SCG-PI'
            elif 'fitting' in cat_lower:
                matching_brand = 'SCG-FT'
            elif 'valve' in cat_lower:
                matching_brand = 'SCG-BV'
            else:
                matching_brand = 'SCG-PI'  # default to pipe
                
        elif 'mizu' in cat_lower:
            if 'fitting' in cat_lower:
                matching_brand = 'MIZU-FT'
            else:
                matching_brand = 'MIZU-PI'
                
        elif 'icon' in cat_lower or 'micon' in cat_lower or 'scala' in cat_lower:
            matching_brand = 'ICON-PI'
            
        elif 'pipe' in cat_lower:
            matching_brand = 'SCG-PI'
        elif 'fitting' in cat_lower:
            matching_brand = 'SCG-FT'
        elif 'valve' in cat_lower:
            matching_brand = 'SCG-BV'
        else:
            matching_brand = category.replace(' ', '-').replace('(', '').replace(')', '').replace('/', '-').upper()

        brand_mapping[category] = matching_brand
        
        # Check historical data availability
        historical_tonnage = historical_summary.get(matching_brand, 0) if historical_summary else 0
        
        # Add to brand_targets_agg
        if matching_brand:
            if matching_brand not in brand_targets_agg:
                brand_targets_agg[matching_brand] = {
                    'mayTarget': 0,
                    'w1Target': 0,
                    'categories': [],
                    'historicalTonnage': historical_tonnage
                }
            
            may_target = targets.get('mayTarget', 0) if isinstance(targets, dict) else 0
            w1_target = targets.get('w1Target', 0) if isinstance(targets, dict) else 0
            
            brand_targets_agg[matching_brand]['mayTarget'] += may_target
            brand_targets_agg[matching_brand]['w1Target'] += w1_target
            brand_targets_agg[matching_brand]['categories'].append(category)
            
            processed_count += 1
    
    # Show results summary
    if processed_count > 0:
        st.success(f"✅ Processed **{processed_count}** MFG categories")
    
    if skipped_count > 0:
        st.info(f"⏭️ Skipped **{skipped_count}** Trading categories")
    
    if not brand_targets_agg:
        st.error("❌ No MFG categories could be processed")
        return {}, {}
    
    # Show Brand Targets summary
    summary_data = []
    for brand, targets in brand_targets_agg.items():
        historical_tonnage = targets['historicalTonnage']
        may_ratio = targets['mayTarget'] / historical_tonnage if historical_tonnage > 0 else 0
        
        summary_data.append({
            'Brand': brand,
            'May Target': targets['mayTarget'],
            'W1 Target': targets['w1Target'],
            'Historical': historical_tonnage,
            'Growth': f"{may_ratio:.1f}x" if historical_tonnage > 0 else "New",
            'Categories': len(targets['categories'])
        })
    
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True)
    
    return brand_mapping, brand_targets_agg

def predict_sku_distribution(brand_targets_agg, historical_df):
    """Predicts SKU distribution based on historical data and new targets."""
    if historical_df is None or historical_df.empty:
        st.error("Historical data not available for prediction")
        return {}, {}

    st.write("📈 **Generating SKU Distribution Predictions...**")
    
    # Create brand/SKU tonnage summary
    brand_sku_tonnage = historical_df.groupby(['BRANDPRODUCT', 'Item Code', 'Item Name'])['TON'].sum().reset_index()
    
    st.write(f"Unique SKUs in historical data: {len(brand_sku_tonnage):,}")
    
    # Create SKU details mapping
    sku_details_map = {}
    for _, row in brand_sku_tonnage.iterrows():
        sku_details_map[row['Item Code']] = {'name': row['Item Name'], 'brand': row['BRANDPRODUCT']}

    # Calculate total tonnage per brand
    brand_total_tonnage = brand_sku_tonnage.groupby('BRANDPRODUCT')['TON'].sum().rename('TotalBrandTon').reset_index()
    
    # Merge and calculate percentages
    brand_sku_percentages = pd.merge(brand_sku_tonnage, brand_total_tonnage, on='BRANDPRODUCT')
    brand_sku_percentages['Percentage'] = brand_sku_percentages['TON'] / brand_sku_percentages['TotalBrandTon']
    
    # Generate predictions
    predictions = {}
    brands_with_no_data = []
    brands_with_high_growth = []
    
    for brand, targets in brand_targets_agg.items():
        may_target_val = targets['mayTarget']
        w1_target_val = targets['w1Target']
        historical_tonnage = targets.get('historicalTonnage', 0)
        
        # Find SKUs for this brand
        current_brand_skus = brand_sku_percentages[brand_sku_percentages['BRANDPRODUCT'] == brand]
        
        if len(current_brand_skus) == 0:
            brands_with_no_data.append(brand)
            st.warning(f"⚠️ No historical data found for Brand: {brand}")
            continue
        
        # Check growth rates
        if historical_tonnage > 0:
            may_growth = may_target_val / historical_tonnage
            w1_growth = w1_target_val / historical_tonnage
            if may_growth > 5 or w1_growth > 5:
                brands_with_high_growth.append((brand, may_growth, w1_growth))
        
        st.write(f"✅ Brand {brand}: Found {len(current_brand_skus)} SKUs in historical data")
        
        predictions[brand] = {
            'mayTarget': may_target_val,
            'w1Target': w1_target_val,
            'historicalTonnage': historical_tonnage,
            'categories': targets['categories'],
            'mayDistribution': {},
            'w1Distribution': {},
            'skuCount': len(current_brand_skus)
        }
        
        # Calculate distribution for each SKU
        for _, sku_row in current_brand_skus.iterrows():
            sku_code = sku_row['Item Code']
            percentage = sku_row['Percentage']
            item_name = sku_row['Item Name']
            historical_sku_tonnage = sku_row['TON']

            # Use threshold of 0.1% = 0.001
            if percentage >= 0.001:
                predicted_tonnage_may = may_target_val * percentage
                predictions[brand]['mayDistribution'][sku_code] = {
                    'tonnage': predicted_tonnage_may,
                    'percentage': percentage,
                    'itemName': item_name,
                    'historicalTonnage': historical_sku_tonnage
                }
                predicted_tonnage_w1 = w1_target_val * percentage
                predictions[brand]['w1Distribution'][sku_code] = {
                    'tonnage': predicted_tonnage_w1,
                    'percentage': percentage,
                    'itemName': item_name,
                    'historicalTonnage': historical_sku_tonnage
                }
    
    # Show prediction summary
    st.write("📋 **Prediction Summary:**")
    prediction_summary = []
    for brand, pred in predictions.items():
        historical_tonnage = pred.get('historicalTonnage', 0)
        growth_may = pred['mayTarget'] / historical_tonnage if historical_tonnage > 0 else 0
        growth_w1 = pred['w1Target'] / historical_tonnage if historical_tonnage > 0 else 0
        
        prediction_summary.append({
            'Brand': brand,
            'SKU Count': pred['skuCount'],
            'May Target': pred['mayTarget'],
            'W1 Target': pred['w1Target'],
            'Historical': historical_tonnage,
            'May Growth': f"{growth_may:.1f}x" if historical_tonnage > 0 else "N/A",
            'W1 Growth': f"{growth_w1:.1f}x" if historical_tonnage > 0 else "N/A"
        })
    
    if prediction_summary:
        pred_df = pd.DataFrame(prediction_summary)
        st.dataframe(pred_df)
    
    # Show warnings
    if brands_with_no_data:
        st.error(f"❌ **Brands with no historical data:** {', '.join(brands_with_no_data)}")
    
    if brands_with_high_growth:
        st.warning("⚠️ **Brands with high growth targets:**")
        for brand, may_growth, w1_growth in brands_with_high_growth:
            st.write(f"   • {brand}: May {may_growth:.1f}x, W1 {w1_growth:.1f}x")
    
    return predictions, sku_details_map

# --- AI Analysis Functions ---
def setup_openai_api():
    """Setup OpenAI API key"""
    if not OPENAI_AVAILABLE:
        return False, "not_installed"
    
    api_key = None
    source = ""
    
    # Check environment variables first
    if OPENAI_API_KEY and OPENAI_API_KEY != "sk-YOUR-API-KEY-HERE":
        api_key = OPENAI_API_KEY
        source = "environment"
    else:
        # Fallback to session state
        api_key = st.session_state.get('openai_api_key')
        if api_key:
            source = "user_input"
    
    if api_key:
        return True, source
    else:
        return False, "no_key"

def generate_insight_analysis(brand_targets_agg, predictions, selected_brand=None):
    """Generate AI-powered insights using OpenAI"""
    
    has_api_key, source = setup_openai_api()
    if not has_api_key:
        if source == "not_installed":
            st.error("❌ OpenAI library not installed")
        else:
            st.error("❌ OpenAI API Key not found. Please set in Environment Variables or enter manually")
        return None
    
    try:
        # Get API key
        api_key = None
        if OPENAI_API_KEY and OPENAI_API_KEY != "sk-YOUR-API-KEY-HERE":
            api_key = OPENAI_API_KEY
        else:
            api_key = st.session_state.get('openai_api_key')
        
        if not api_key:
            st.error("❌ API Key not found")
            return None
        
        # Prepare analysis data
        analysis_data = {
            "brand_summary": {},
            "total_targets": {"may": 0, "w1": 0},
            "growth_analysis": {},
            "risk_assessment": {}
        }
        
        # Summarize by Brand
        for brand, targets in brand_targets_agg.items():
            historical = targets.get('historicalTonnage', 0)
            may_target = targets['mayTarget']
            w1_target = targets['w1Target']
            
            analysis_data["brand_summary"][brand] = {
                "may_target": may_target,
                "w1_target": w1_target,
                "historical": historical,
                "may_growth": may_target / historical if historical > 0 else 0,
                "w1_growth": w1_target / historical if historical > 0 else 0,
                "categories": targets.get('categories', [])
            }
            
            analysis_data["total_targets"]["may"] += may_target
            analysis_data["total_targets"]["w1"] += w1_target
        
        # Add SKU data if brand is selected
        if selected_brand and selected_brand in predictions:
            pred_data = predictions[selected_brand]
            may_dist = pred_data.get('mayDistribution', {})
            
            # Top 5 SKU
            top_skus = sorted(may_dist.items(), key=lambda x: x[1]['tonnage'], reverse=True)[:5]
            analysis_data["top_skus"] = [
                {
                    "sku": sku, 
                    "tonnage": data['tonnage'], 
                    "percentage": data['percentage'],
                    "name": data['itemName']
                } 
                for sku, data in top_skus
            ]
        
        # Create prompt for OpenAI
        prompt = f"""
        You are an expert in production planning analysis for a PVC pipe and fitting manufacturing company.

        Analysis Data:
        {json.dumps(analysis_data, ensure_ascii=False, indent=2)}

        Please analyze and provide insights on the following aspects:

        1. **Overall Growth**: Analyze growth of each Brand and opportunities/risks
        2. **Distribution**: Evaluate target distribution across different Brands
        3. **Strategic Recommendations**: Suggest production improvements and resource management
        4. **Readiness**: What should be prepared to achieve targets
        5. **Risk Points**: Risks or issues that may arise

        Provide answer in English, approximately 500-700 words, professional tone.
        """
        
        # Call OpenAI API (v1.0+ syntax)
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in production planning and business strategy analysis"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        st.error(f"❌ Error calling OpenAI API: {e}")
        return None

def display_insights_section(brand_targets_agg, predictions, selected_brand):
    """Display AI insights section"""
    
    st.subheader("🤖 AI Insights Analysis")
    
    # Check if OpenAI library is installed
    if not OPENAI_AVAILABLE:
        st.error("❌ OpenAI library not installed")
        st.markdown("""
        **📦 How to fix:**
        
        **For Render:**
        1. Create `requirements.txt` file in project folder
        2. Add this line:
        ```
        streamlit
        pandas
        plotly
        openai>=1.0.0
        ```
        3. Commit and push to GitHub
        4. Render will install automatically
        
        **For Local:**
        ```bash
        pip install openai
        ```
        """)
        return
    
    # Check API Key
    has_api_key, source = setup_openai_api()
    
    if has_api_key and source == "environment":
        st.success("✅ OpenAI API Key ready (from Environment Variables)")
        analyze_button = st.button("🔍 Start AI Analysis", type="primary", use_container_width=True)
        
    elif has_api_key and source == "user_input":
        st.info("🔑 Using provided API Key")
        analyze_button = st.button("🔍 Start AI Analysis", type="primary", use_container_width=True)
        
    else:
        st.warning("⚠️ OpenAI API Key required for this feature")
        
        with st.expander("🔧 How to set API Key", expanded=True):
            st.markdown("""
            **🚀 Method 1: Render Environment Variables (Recommended for Render)**
            
            1. In Render Dashboard → Go to your Service
            2. Click **Environment** tab
            3. Add Environment Variable:
               - **Key**: `OPENAI_API_KEY`
               - **Value**: `sk-proj-your-api-key-here`
            4. Click **Save Changes** (Render will redeploy automatically)
            """)
            
            st.markdown("---")
            st.markdown("**🔑 Method 2: Temporary Input**")
            
            if 'openai_api_key' not in st.session_state:
                st.session_state.openai_api_key = ""
            
            api_key = st.text_input(
                "OpenAI API Key (temporary):",
                value=st.session_state.openai_api_key,
                type="password",
                help="This API Key will not be stored permanently"
            )
            st.session_state.openai_api_key = api_key
            
        analyze_button = st.button("🔍 Start AI Analysis", type="primary", use_container_width=True)
    
    if analyze_button:
        has_api_key, source = setup_openai_api()
        if not has_api_key:
            if source == "not_installed":
                st.error("❌ Please install OpenAI library first")
            else:
                st.error("❌ Please set OpenAI API Key first")
        else:
            with st.spinner("🤖 AI is analyzing data insights..."):
                insights = generate_insight_analysis(brand_targets_agg, predictions, selected_brand)
                
                if insights:
                    st.success("✅ Analysis completed!")
                    
                    st.markdown("### 📊 AI Insights & Strategic Recommendations")
                    
                    with st.container():
                        st.markdown(insights)
                    
                    st.session_state.ai_insights = insights
                    
                    st.divider()
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        st.download_button(
                            label="📥 Download AI Analysis Report",
                            data=insights,
                            file_name=f"ai_insights_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
    
    # Show saved analysis (if available)
    if st.session_state.get('ai_insights'):
        st.divider()
        st.markdown("### 📈 Latest Analysis Report")
        with st.expander("📋 View Full AI Analysis Report", expanded=True):
            st.markdown(st.session_state.ai_insights)
    
    st.info("""
    **🧠 AI Analysis provides insights on:**
    - 📈 Growth analysis and trends
    - ⚠️ Risk assessment and opportunities  
    - 🎯 Strategic recommendations for production
    - 🔧 Readiness preparation and improvements
    - 💡 Specific insights for PVC pipe and fitting business
    """)

def create_executive_summary(brand_targets_agg, predictions):
    """Create executive summary for the analysis"""
    
    summary_data = {
        "total_brands": len(brand_targets_agg),
        "total_skus": sum(len(pred.get('mayDistribution', {})) for pred in predictions.values()),
        "may_total": sum(targets['mayTarget'] for targets in brand_targets_agg.values()),
        "w1_total": sum(targets['w1Target'] for targets in brand_targets_agg.values()),
        "historical_total": sum(targets.get('historicalTonnage', 0) for targets in brand_targets_agg.values()),
    }
    
    # Calculate growth
    if summary_data["historical_total"] > 0:
        may_growth = summary_data["may_total"] / summary_data["historical_total"]
        w1_growth = summary_data["w1_total"] / summary_data["historical_total"]
    else:
        may_growth = w1_growth = 0
    
    # Show Executive Summary
    st.markdown("### 📋 Executive Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🏭 Brands", summary_data["total_brands"])
    with col2:
        st.metric("📦 SKUs", summary_data["total_skus"])
    with col3:
        st.metric("🎯 May Target", f"{summary_data['may_total']:.1f} tons")
    with col4:
        st.metric("📅 W1 Target", f"{summary_data['w1_total']:.1f} tons")
    
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("📈 Historical", f"{summary_data['historical_total']:.1f} tons")
    with col6:
        st.metric("📊 May Growth", f"{may_growth:.1f}x")
    with col7:
        st.metric("📈 W1 Growth", f"{w1_growth:.1f}x")
    with col8:
        risk_level = "🔴 High" if may_growth > 5 or w1_growth > 5 else "🟡 Medium" if may_growth > 3 or w1_growth > 3 else "🟢 Low"
        st.metric("⚠️ Risk Level", risk_level)
    
    return summary_data

def generate_excel_download(predictions_data, selected_period_key):
    """Generates an Excel file for download from the predictions."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Create summary sheet
        summary_data = []
        for brand, data in predictions_data.items():
            period_dist_key = 'mayDistribution' if selected_period_key == 'may' else 'w1Distribution'
            target_key = 'mayTarget' if selected_period_key == 'may' else 'w1Target'
            
            summary_data.append({
                'Brand': brand,
                'Target (Tons)': data[target_key],
                'Historical (Tons)': data.get('historicalTonnage', 0),
                'SKU Count': len(data.get(period_dist_key, {})),
                'Categories': ', '.join(data.get('categories', []))
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, index=False, sheet_name='Summary')
        
        # Create sheet for each brand
        for brand, data in predictions_data.items():
            period_dist_key = 'mayDistribution' if selected_period_key == 'may' else 'w1Distribution'
            dist_data = data.get(period_dist_key)

            if dist_data:
                df_dist = pd.DataFrame.from_dict(dist_data, orient='index').reset_index()
                
                rename_map = {
                    'index': 'SKU',
                    'itemName': 'Product Name',
                    'tonnage': 'Predicted Tonnage',
                    'percentage': 'Percentage (%)',
                    'historicalTonnage': 'Historical Tonnage'
                }
                
                df_dist.rename(columns=rename_map, inplace=True)
                
                if 'Percentage (%)' in df_dist.columns:
                    df_dist['Percentage (%)'] = (df_dist['Percentage (%)'] * 100).round(2)
                
                if 'Predicted Tonnage' in df_dist.columns:
                    df_dist['Predicted Tonnage'] = df_dist['Predicted Tonnage'].round(4)
                
                if 'Historical Tonnage' in df_dist.columns:
                    df_dist['Historical Tonnage'] = df_dist['Historical Tonnage'].round(4)
                
                df_dist = df_dist.sort_values(by='Predicted Tonnage', ascending=False)
                
                # Add Growth Ratio column
                if 'Historical Tonnage' in df_dist.columns and 'Predicted Tonnage' in df_dist.columns:
                    df_dist['Growth Ratio'] = (df_dist['Predicted Tonnage'] / df_dist['Historical Tonnage']).round(2)
                    df_dist['Growth Ratio'] = df_dist['Growth Ratio'].replace([float('inf'), -float('inf')], 'N/A')
                
                final_columns_order = ['SKU', 'Product Name', 'Predicted Tonnage', 'Historical Tonnage', 'Growth Ratio', 'Percentage (%)']
                output_df = df_dist.reindex(columns=[col for col in final_columns_order if col in df_dist.columns])
                
                sheet_name = brand.replace('/', '-').replace('\\', '-')
                sheet_name = sheet_name[:31]
                
                output_df.to_excel(writer, index=False, sheet_name=sheet_name)
    
    processed_data = output.getvalue()
    return processed_data

# --- Streamlit App UI ---
st.set_page_config(layout="wide", page_title="Production Planning App")
st.title("🏭 Production Planning Application")
st.markdown("📊 Analyze historical data and targets to create precise SKU-level production plans")

# Initialize session state variables
if 'historical_df' not in st.session_state:
    st.session_state.historical_df = None
if 'category_targets' not in st.session_state:
    st.session_state.category_targets = None
if 'brand_targets_agg' not in st.session_state:
    st.session_state.brand_targets_agg = None
if 'predictions' not in st.session_state:
    st.session_state.predictions = None
if 'selected_period' not in st.session_state:
    st.session_state.selected_period = 'may'
if 'selected_brand' not in st.session_state:
    st.session_state.selected_brand = None
if 'show_all_skus' not in st.session_state:
    st.session_state.show_all_skus = False

tab1, tab2, tab3 = st.tabs(["1. 📁 Upload Data", "2. 📊 Analysis", "3. 📋 Results"])

with tab1:
    st.header("📁 Upload Data Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Historical Data File")
        st.markdown("**Expected Excel format:**")
        st.markdown("- Headers: BRANDPRODUCT, Item Code, Item Name, TON")
        
        historical_file_upload = st.file_uploader(
            "Upload Historical Data Excel File", 
            type=['xlsx', 'xls'], 
            key="historical_uploader",
            help="Excel file with historical delivery data"
        )
        
        if historical_file_upload:
            st.session_state.historical_df = process_historical_file(historical_file_upload)
            if st.session_state.historical_df is not None:
                st.success(f"✅ Historical data loaded: '{historical_file_upload.name}'")

    with col2:
        st.subheader("🎯 Target Data File")
        st.markdown("**Expected BNI Sales Rolling format:**")
        st.markdown("- Headers: May, W1, W2, W3, W4 columns")
        
        target_file_upload = st.file_uploader(
            "Upload Target Data Excel File", 
            type=['xlsx', 'xls'], 
            key="target_uploader",
            help="BNI Sales Rolling file with MFG category targets"
        )
        
        if target_file_upload:
            st.session_state.category_targets = process_target_file(target_file_upload)
            if st.session_state.category_targets:
                st.success(f"✅ Target data loaded: '{target_file_upload.name}'")
                # Auto-map when target file is uploaded
                if st.session_state.historical_df is not None:
                    _, st.session_state.brand_targets_agg = map_categories_to_historical_brands(
                        st.session_state.category_targets, 
                        st.session_state.historical_df
                    )

    st.divider()
    
    # Generate SKU Distribution button
    generate_disabled = not (st.session_state.historical_df is not None and st.session_state.category_targets is not None)
    
    if st.button(
        "🚀 Generate SKU Distribution", 
        disabled=generate_disabled,
        type="primary",
        use_container_width=True
    ):
        with st.spinner("Processing and generating predictions..."):
            try:
                # Validate data
                if st.session_state.category_targets is None:
                    st.error("❌ No category targets data found")
                    st.stop()
                
                if st.session_state.historical_df is None:
                    st.error("❌ No historical data found")
                    st.stop()
                
                # Create brand mapping if not done
                if st.session_state.brand_targets_agg is None:
                    _, st.session_state.brand_targets_agg = map_categories_to_historical_brands(
                        st.session_state.category_targets, 
                        st.session_state.historical_df
                    )

                # Validate brand mapping results
                if not st.session_state.brand_targets_agg:
                    st.error("❌ Could not create brand targets - please check data")
                    st.write("**Possible causes:**")
                    st.write("1. Target file has no MFG categories")
                    st.write("2. Category to brand mapping failed")
                    st.write("3. Incorrect file format")
                    st.stop()
                
                # Generate predictions
                st.session_state.predictions, _ = predict_sku_distribution(
                    st.session_state.brand_targets_agg, 
                    st.session_state.historical_df
                )
                
                if st.session_state.predictions:
                    st.success("🎉 SKU distribution generation completed! Go to 'Analysis' or 'Results' tab")
                    st.session_state.selected_brand = next(iter(st.session_state.predictions), None)
                    st.balloons()
                else:
                    st.warning("⚠️ Prediction generation completed but no usable results")
                    
            except Exception as e:
                st.error(f"❌ Error during processing: {e}")
                import traceback
                st.error(f"Details: {traceback.format_exc()}")
    
    # Data status display
    if st.session_state.historical_df is not None or st.session_state.category_targets is not None:
        st.divider()
        st.subheader("📊 Data Status")
        col1, col2, col3 = st.columns(3)
        with col1:
            hist_status = f"{len(st.session_state.historical_df)} records" if st.session_state.historical_df is not None else "Not loaded"
            st.metric("📈 Historical Data", hist_status)
        with col2:
            target_status = f"{len(st.session_state.category_targets)} categories" if st.session_state.category_targets is not None else "Not loaded"
            st.metric("🎯 Target Data", target_status)
        with col3:
            ready_status = "Ready" if st.session_state.brand_targets_agg else "Not ready"
            st.metric("🚀 Status", ready_status)

# Common functions
def create_period_selector(widget_key):
    period_options = {'may': 'May 📅', 'w1': 'Week 1 📆'}
    period_keys = list(period_options.keys())
    try:
        current_period_index = period_keys.index(st.session_state.selected_period)
    except ValueError:
        current_period_index = 0
        st.session_state.selected_period = period_keys[0]
    
    st.session_state.selected_period = st.radio(
        "Select Period:",
        options=period_keys,
        format_func=lambda x: period_options[x],
        horizontal=True,
        index=current_period_index,
        key=widget_key
    )
    return period_options[st.session_state.selected_period]

def create_brand_selector(widget_key):
    if not st.session_state.predictions:
        return None
        
    brand_list = list(st.session_state.predictions.keys())
    if not brand_list:
        st.warning("No prediction data available for any brand")
        return None

    if st.session_state.selected_brand not in brand_list:
         st.session_state.selected_brand = brand_list[0] if brand_list else None
    
    try:
        current_brand_index = brand_list.index(st.session_state.selected_brand) if st.session_state.selected_brand else 0
    except ValueError:
        current_brand_index = 0
        st.session_state.selected_brand = brand_list[0] if brand_list else None

    st.session_state.selected_brand = st.selectbox(
        "Select Brand:", 
        options=brand_list,
        index=current_brand_index,
        key=widget_key
    )
    return st.session_state.selected_brand

with tab2:
    st.header("📊 Data Analysis")
    if not st.session_state.predictions:
        st.info("📝 Please upload data and generate SKU distribution in the 'Upload Data' tab first")
    else:
        # Executive Summary
        create_executive_summary(st.session_state.brand_targets_agg, st.session_state.predictions)
        
        st.divider()
        
        selected_period_name = create_period_selector("analysis_period_selector")
        
        st.subheader("📈 Brand Target Distribution")
        if st.session_state.brand_targets_agg:
            brand_target_data = []
            target_key = 'mayTarget' if st.session_state.selected_period == 'may' else 'w1Target'
            for brand, targets in st.session_state.brand_targets_agg.items():
                if targets[target_key] > 0:
                    brand_target_data.append({'Brand': brand, 'Tonnage': targets[target_key]})
            
            if brand_target_data:
                df_brand_targets = pd.DataFrame(brand_target_data)
                fig_brand_targets = px.bar(
                    df_brand_targets, 
                    x='Brand', 
                    y='Tonnage', 
                    title=f"Brand Targets for {selected_period_name}",
                    labels={'Tonnage':'Tons'},
                    color='Tonnage',
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(fig_brand_targets, use_container_width=True)

        st.divider()
        st.subheader("🎯 SKU Distribution")
        
        col_brand_sel, col_toggle_sku = st.columns([3,1])
        with col_brand_sel:
            selected_brand = create_brand_selector("analysis_brand_selector")
        with col_toggle_sku:
             st.session_state.show_all_skus = st.checkbox("Show All SKUs", value=st.session_state.show_all_skus, key="show_all_skus_toggle")

        if selected_brand:
            brand_data = st.session_state.predictions.get(selected_brand)
            dist_key = 'mayDistribution' if st.session_state.selected_period == 'may' else 'w1Distribution'
            sku_distribution = brand_data.get(dist_key)

            if sku_distribution:
                df_sku_dist = pd.DataFrame.from_dict(sku_distribution, orient='index').reset_index()
                df_sku_dist.rename(columns={
                    'index': 'SKU', 
                    'itemName': 'Product Name', 
                    'tonnage': 'Predicted Tonnage', 
                    'percentage': 'Percentage',
                    'historicalTonnage': 'Historical Tonnage'
                }, inplace=True)
                df_sku_dist = df_sku_dist.sort_values(by='Predicted Tonnage', ascending=False)
                
                # Add Growth Ratio column
                if 'Historical Tonnage' in df_sku_dist.columns:
                    df_sku_dist['Growth Ratio'] = (df_sku_dist['Predicted Tonnage'] / df_sku_dist['Historical Tonnage']).round(2)
                    df_sku_dist['Growth Ratio'] = df_sku_dist['Growth Ratio'].replace([float('inf')], 999.0)
                
                display_df_sku = df_sku_dist if st.session_state.show_all_skus else df_sku_dist.head(15)
                
                if not display_df_sku.empty:
                    # Show statistics summary
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("SKU Count", len(df_sku_dist))
                    with col2:
                        total_target = df_sku_dist['Predicted Tonnage'].sum()
                        st.metric("Total Target", f"{total_target:.1f} tons")
                    with col3:
                        total_historical = df_sku_dist['Historical Tonnage'].sum()
                        st.metric("Total Historical", f"{total_historical:.1f} tons")
                    with col4:
                        overall_growth = total_target / total_historical if total_historical > 0 else 0
                        st.metric("Growth", f"{overall_growth:.1f}x")
                    
                    # Bar chart
                    fig_sku_bar = px.bar(
                        display_df_sku, 
                        y='SKU', 
                        x='Predicted Tonnage', 
                        orientation='h',
                        title=f"SKU Distribution for {selected_brand} ({selected_period_name})",
                        labels={'Predicted Tonnage':'Tons'}, 
                        hover_data=['Product Name', 'Historical Tonnage', 'Growth Ratio'],
                        color='Growth Ratio',
                        color_continuous_scale='RdYlGn_r'
                    )
                    fig_sku_bar.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
                    st.plotly_chart(fig_sku_bar, use_container_width=True)

                    # Pie chart (Top SKUs)
                    top_n_pie = 8
                    df_pie_data = df_sku_dist.head(top_n_pie).copy()
                    if len(df_sku_dist) > top_n_pie:
                        others_tonnage = df_sku_dist.iloc[top_n_pie:]['Predicted Tonnage'].sum()
                        if others_tonnage > 0.01:
                            others_row = pd.DataFrame([{
                                'SKU': 'Others', 
                                'Product Name': f'Others ({len(df_sku_dist) - top_n_pie} SKUs)', 
                                'Predicted Tonnage': others_tonnage, 
                                'Percentage': 0.0
                            }])
                            df_pie_data = pd.concat([df_pie_data, others_row], ignore_index=True)

                    fig_sku_pie = px.pie(
                        df_pie_data, 
                        values='Predicted Tonnage', 
                        names='SKU', 
                        title=f"Top SKU Proportion for {selected_brand} ({selected_period_name})", 
                        hover_data=['Product Name']
                    )
                    st.plotly_chart(fig_sku_pie, use_container_width=True)
                    
                    # Data table
                    st.subheader("📋 SKU Details")
                    display_columns = ['SKU', 'Product Name', 'Predicted Tonnage', 'Historical Tonnage', 'Growth Ratio', 'Percentage']
                    display_table = display_df_sku[display_columns].copy()
                    display_table['Predicted Tonnage'] = display_table['Predicted Tonnage'].round(3)
                    display_table['Historical Tonnage'] = display_table['Historical Tonnage'].round(3)
                    display_table['Percentage'] = (display_table['Percentage'] * 100).round(2)
                    
                    st.dataframe(display_table, use_container_width=True)
            else:
                st.warning(f"No SKU distribution data for {selected_brand} in {selected_period_name}")

        st.divider()
        
        # AI Insights Analysis Section
        if st.session_state.brand_targets_agg and st.session_state.predictions:
            display_insights_section(
                st.session_state.brand_targets_agg, 
                st.session_state.predictions, 
                selected_brand
            )

with tab3:
    st.header("📋 Production Plan Results")
    if not st.session_state.predictions:
        st.info("📝 Please upload data and generate SKU distribution in the 'Upload Data' tab first")
    else:
        selected_period_name_results = create_period_selector("results_period_selector")
        selected_brand_res = create_brand_selector("results_brand_selector")

        if selected_brand_res:
            brand_data_res = st.session_state.predictions.get(selected_brand_res)
            dist_key_res = 'mayDistribution' if st.session_state.selected_period == 'may' else 'w1Distribution'
            sku_distribution_res = brand_data_res.get(dist_key_res)

            if sku_distribution_res:
                st.subheader(f"📊 Production Plan: {selected_brand_res} - {selected_period_name_results}")
                
                df_results = pd.DataFrame.from_dict(sku_distribution_res, orient='index').reset_index()
                df_results.rename(columns={
                    'index': 'SKU Code', 
                    'itemName': 'Product Name', 
                    'tonnage': 'Production Plan (tons)', 
                    'percentage': 'Proportion (%)',
                    'historicalTonnage': 'Historical Data (tons)'
                }, inplace=True)
                
                # Calculate Growth Ratio
                df_results['Growth Ratio'] = (df_results['Production Plan (tons)'] / df_results['Historical Data (tons)']).round(2)
                df_results['Growth Ratio'] = df_results['Growth Ratio'].replace([float('inf')], 999.0)
                
                # Format data
                df_results['Proportion (%)'] = (df_results['Proportion (%)'] * 100).round(2)
                df_results['Production Plan (tons)'] = df_results['Production Plan (tons)'].round(3)
                df_results['Historical Data (tons)'] = df_results['Historical Data (tons)'].round(3)
                
                # Sort by production plan
                df_results = df_results.sort_values(by='Production Plan (tons)', ascending=False)
                
                # Show summary statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("🎯 Total Target", f"{df_results['Production Plan (tons)'].sum():.1f} tons")
                with col2:
                    st.metric("📈 Historical Total", f"{df_results['Historical Data (tons)'].sum():.1f} tons")
                with col3:
                    total_growth = df_results['Production Plan (tons)'].sum() / df_results['Historical Data (tons)'].sum()
                    st.metric("📊 Overall Growth", f"{total_growth:.1f}x")
                with col4:
                    st.metric("🔢 SKU Count", len(df_results))
                
                # Data filtering
                filter_option = st.selectbox(
                    "Filter Data:",
                    ["All", "Production > 1 ton", "Production > 0.5 ton", "Growth > 3x", "Top 20 SKU"]
                )
                
                if filter_option == "Production > 1 ton":
                    df_display = df_results[df_results['Production Plan (tons)'] > 1]
                elif filter_option == "Production > 0.5 ton":
                    df_display = df_results[df_results['Production Plan (tons)'] > 0.5]
                elif filter_option == "Growth > 3x":
                    df_display = df_results[df_results['Growth Ratio'] > 3]
                elif filter_option == "Top 20 SKU":
                    df_display = df_results.head(20)
                else:
                    df_display = df_results
                
                # Show table
                st.dataframe(
                    df_display[['SKU Code', 'Product Name', 'Production Plan (tons)', 'Historical Data (tons)', 'Growth Ratio', 'Proportion (%)']],
                    use_container_width=True,
                    height=400
                )
                
                # Show warnings for high growth SKUs
                high_growth_skus = df_results[df_results['Growth Ratio'] > 5]
                if len(high_growth_skus) > 0:
                    st.warning(f"⚠️ **Found SKUs with very high growth ({len(high_growth_skus)} items):**")
                    st.dataframe(
                        high_growth_skus[['SKU Code', 'Product Name', 'Production Plan (tons)', 'Growth Ratio']].head(10),
                        use_container_width=True
                    )
            else:
                st.warning(f"No results data for {selected_brand_res}")

        # Excel download section
        if st.session_state.predictions:
            st.divider()
            st.subheader("📥 Download Results")
            
            col_download1, col_download2 = st.columns(2)
            
            with col_download1:
                excel_bytes = generate_excel_download(st.session_state.predictions, st.session_state.selected_period)
                st.download_button(
                    label="📊 Download Complete Results as Excel",
                    data=excel_bytes,
                    file_name=f"production_plan_{st.session_state.selected_period}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
            
            with col_download2:
                st.info("**Excel file contains:**\n"
                       "- Summary: Overview of all brands\n"  
                       "- Individual Brand sheets: Detailed SKU data with comparisons\n"
                       "- Growth Ratio: Growth rate for each SKU")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>🏭 <strong>Production Planning App</strong> | 
    📊 Analyze historical data to predict production requirements | 
    🎯 Precise SKU-level production planning</p>
</div>
""", unsafe_allow_html=True)
