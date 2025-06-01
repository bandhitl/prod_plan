# Production Planning Application - English Version
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
    openai = None
    st.warning("⚠️ OpenAI library not installed - AI Analysis will not be available")

# Configuration
HISTORICAL_REQUIRED_COLS = ["BRANDPRODUCT", "Item Code", "TON", "Item Name"]

# Get API key from environment
OPENAI_API_KEY = None
try:
    import os
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        try:
            OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")
        except:
            pass
except:
    pass

def process_historical_file(uploaded_file):
    """Process uploaded historical data Excel file"""
    try:
        # Try different header positions
        header_positions = [0, 1, 2]
        df = None
        
        for header_pos in header_positions:
            try:
                temp_df = pd.read_excel(uploaded_file, header=header_pos)
                cols_found = sum(1 for col in HISTORICAL_REQUIRED_COLS 
                               if any(req_col.upper() in str(temp_col).upper() 
                                     for temp_col in temp_df.columns 
                                     for req_col in [col]))
                
                if cols_found >= 3:
                    df = temp_df
                    st.success(f"✅ Found valid headers at row {header_pos + 1}")
                    break
            except:
                continue
        
        if df is None:
            st.error("❌ Could not find valid headers in the file")
            return None
        
        # Map columns
        column_mapping = {}
        for req_col in HISTORICAL_REQUIRED_COLS:
            for df_col in df.columns:
                if req_col.upper() in str(df_col).upper():
                    column_mapping[df_col] = req_col
                    break
        
        df = df.rename(columns=column_mapping)
        
        # Check required columns
        missing_cols = [col for col in HISTORICAL_REQUIRED_COLS if col not in df.columns]
        if missing_cols:
            st.error(f"Missing required columns: {', '.join(missing_cols)}")
            return None
        
        # Clean data
        original_count = len(df)
        df['TON'] = pd.to_numeric(df['TON'], errors='coerce')
        df = df.dropna(subset=['TON'])
        df = df[df['TON'] > 0]
        df = df.dropna(subset=['BRANDPRODUCT', 'Item Code'])
        df = df[df['BRANDPRODUCT'].astype(str).str.strip() != '']
        df = df[df['Item Code'].astype(str).str.strip() != '']
        
        st.write(f"📊 **Data Summary:** {len(df):,} valid records from {original_count:,} total rows")
        
        # Brand summary
        brand_summary = df.groupby('BRANDPRODUCT').agg({
            'Item Code': 'nunique',
            'TON': ['count', 'sum']
        }).round(2)
        brand_summary.columns = ['Unique SKUs', 'Records', 'Total TON']
        brand_summary = brand_summary.sort_values('Total TON', ascending=False)
        
        st.dataframe(brand_summary, use_container_width=True)
        return df
        
    except Exception as e:
        st.error(f"Error processing historical file: {e}")
        return None

def process_target_file(uploaded_file):
    """Process BNI Sales Rolling target file"""
    try:
        df = pd.read_excel(uploaded_file, sheet_name=0, header=None)
        
        st.write("🔍 **Target File Preview:**")
        st.dataframe(df.head(10))
        
        if len(df) < 3:
            st.error("❌ File has insufficient data")
            return None
        
        # Find May and W1 columns
        may_col_idx = None
        w1_col_idx = None
        
        for row_idx in range(min(3, len(df))):
            for col_idx in range(len(df.columns)):
                cell_value = str(df.iloc[row_idx, col_idx]).strip().lower()
                if 'may' in cell_value and may_col_idx is None:
                    may_col_idx = col_idx
                elif 'w1' in cell_value and w1_col_idx is None:
                    w1_col_idx = col_idx
        
        if may_col_idx is None:
            may_col_idx = 1
        if w1_col_idx is None:
            w1_col_idx = 2
        
        # Find data range
        start_row_idx = 2
        end_row_idx = len(df)
        
        for i in range(start_row_idx, len(df)):
            if i < len(df):
                cell_value = str(df.iloc[i, 0]).strip().lower()
                if 'total' in cell_value:
                    end_row_idx = i
                    break
        
        # Extract categories
        category_data = []
        for i in range(start_row_idx, end_row_idx):
            if i < len(df):
                category_name = df.iloc[i, 0]
                may_value = df.iloc[i, may_col_idx] if may_col_idx < len(df.columns) else 0
                w1_value = df.iloc[i, w1_col_idx] if w1_col_idx < len(df.columns) else 0
                
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
        
        if category_data:
            st.write(f"📋 **Extracted {len(category_data)} categories**")
            
            category_targets = {}
            for item in category_data:
                category_targets[item['Category']] = {
                    'mayTarget': item['MayTarget'],
                    'w1Target': item['W1Target']
                }
            
            return category_targets
        else:
            st.error("❌ No category data found")
            return None
            
    except Exception as e:
        st.error(f"Error processing target file: {e}")
        return None

def map_categories_to_brands(category_targets, historical_df):
    """Map categories to brands"""
    historical_summary = {}
    if historical_df is not None and not historical_df.empty:
        try:
            hist_summary = historical_df.groupby('BRANDPRODUCT')['TON'].sum()
            historical_summary = hist_summary.to_dict()
        except Exception as e:
            st.error(f"Error creating historical summary: {e}")
            historical_summary = {}
    
    brand_targets_agg = {}
    processed_count = 0
    skipped_count = 0
    
    for category, targets in category_targets.items():
        cat_lower = str(category).lower().strip()
        
        if 'mfg' not in cat_lower:
            skipped_count += 1
            continue
        
        # Determine brand
        if 'scg' in cat_lower:
            if 'pipe' in cat_lower or 'conduit' in cat_lower:
                matching_brand = 'SCG-PI'
            elif 'fitting' in cat_lower:
                matching_brand = 'SCG-FT'
            elif 'valve' in cat_lower:
                matching_brand = 'SCG-BV'
            else:
                matching_brand = 'SCG-PI'
        elif 'mizu' in cat_lower:
            if 'fitting' in cat_lower:
                matching_brand = 'MIZU-FT'
            else:
                matching_brand = 'MIZU-PI'
        elif 'icon' in cat_lower or 'micon' in cat_lower:
            matching_brand = 'ICON-PI'
        elif 'pipe' in cat_lower:
            matching_brand = 'SCG-PI'
        elif 'fitting' in cat_lower:
            matching_brand = 'SCG-FT'
        elif 'valve' in cat_lower:
            matching_brand = 'SCG-BV'
        else:
            matching_brand = category.replace(' ', '-').upper()

        historical_tonnage = historical_summary.get(matching_brand, 0)
        
        if matching_brand not in brand_targets_agg:
            brand_targets_agg[matching_brand] = {
                'mayTarget': 0,
                'w1Target': 0,
                'categories': [],
                'historicalTonnage': historical_tonnage
            }
        
        may_target = targets.get('mayTarget', 0)
        w1_target = targets.get('w1Target', 0)
        
        brand_targets_agg[matching_brand]['mayTarget'] += may_target
        brand_targets_agg[matching_brand]['w1Target'] += w1_target
        brand_targets_agg[matching_brand]['categories'].append(category)
        
        processed_count += 1
    
    if processed_count > 0:
        st.success(f"✅ Processed {processed_count} MFG categories")
    
    if skipped_count > 0:
        st.info(f"⏭️ Skipped {skipped_count} Trading categories")
    
    if brand_targets_agg:
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
        
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
    
    return {}, brand_targets_agg

def predict_sku_distribution(brand_targets_agg, historical_df):
    """Predict SKU distribution"""
    if historical_df is None or historical_df.empty:
        st.error("Historical data not available for prediction")
        return {}, {}

    st.write("📈 **Generating SKU Distribution Predictions...**")
    
    brand_sku_tonnage = historical_df.groupby(['BRANDPRODUCT', 'Item Code', 'Item Name'])['TON'].sum().reset_index()
    brand_total_tonnage = brand_sku_tonnage.groupby('BRANDPRODUCT')['TON'].sum().rename('TotalBrandTon').reset_index()
    brand_sku_percentages = pd.merge(brand_sku_tonnage, brand_total_tonnage, on='BRANDPRODUCT')
    brand_sku_percentages['Percentage'] = brand_sku_percentages['TON'] / brand_sku_percentages['TotalBrandTon']
    
    predictions = {}
    
    for brand, targets in brand_targets_agg.items():
        current_brand_skus = brand_sku_percentages[brand_sku_percentages['BRANDPRODUCT'] == brand]
        
        if len(current_brand_skus) == 0:
            st.warning(f"⚠️ No historical data for {brand}")
            continue
        
        predictions[brand] = {
            'mayTarget': targets['mayTarget'],
            'w1Target': targets['w1Target'],
            'historicalTonnage': targets.get('historicalTonnage', 0),
            'categories': targets['categories'],
            'mayDistribution': {},
            'w1Distribution': {},
            'skuCount': len(current_brand_skus)
        }
        
        for _, sku_row in current_brand_skus.iterrows():
            sku_code = sku_row['Item Code']
            percentage = sku_row['Percentage']
            item_name = sku_row['Item Name']
            historical_sku_tonnage = sku_row['TON']

            if percentage >= 0.001:
                predictions[brand]['mayDistribution'][sku_code] = {
                    'tonnage': targets['mayTarget'] * percentage,
                    'percentage': percentage,
                    'itemName': item_name,
                    'historicalTonnage': historical_sku_tonnage
                }
                predictions[brand]['w1Distribution'][sku_code] = {
                    'tonnage': targets['w1Target'] * percentage,
                    'percentage': percentage,
                    'itemName': item_name,
                    'historicalTonnage': historical_sku_tonnage
                }
    
    st.success(f"✅ Generated predictions for {len(predictions)} brands")
    return predictions, {}

# Streamlit App
st.set_page_config(layout="wide", page_title="Production Planning App")
st.title("🏭 Production Planning Application")
st.markdown("📊 Analyze historical data and targets to create precise SKU-level production plans")

# Initialize session state
for key in ['historical_df', 'category_targets', 'brand_targets_agg', 'predictions', 'selected_period', 'selected_brand']:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'selected_period' else 'may'

tab1, tab2, tab3 = st.tabs(["1. 📁 Upload Data", "2. 📊 Analysis", "3. 📋 Results"])

with tab1:
    st.header("📁 Upload Data Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Historical Data")
        historical_file = st.file_uploader("Upload Historical Excel File", type=['xlsx', 'xls'], key="hist")
        
        if historical_file:
            st.session_state.historical_df = process_historical_file(historical_file)
            if st.session_state.historical_df is not None:
                st.success(f"✅ Historical data loaded: '{historical_file.name}'")

    with col2:
        st.subheader("🎯 Target Data")
        target_file = st.file_uploader("Upload Target Excel File", type=['xlsx', 'xls'], key="target")
        
        if target_file:
            st.session_state.category_targets = process_target_file(target_file)
            if st.session_state.category_targets:
                st.success(f"✅ Target data loaded: '{target_file.name}'")
                if st.session_state.historical_df is not None:
                    _, st.session_state.brand_targets_agg = map_categories_to_brands(
                        st.session_state.category_targets, st.session_state.historical_df)

    st.divider()
    
    # Generate button
    generate_disabled = not (st.session_state.historical_df is not None and st.session_state.category_targets is not None)
    
    if st.button("🚀 Generate SKU Distribution", disabled=generate_disabled, type="primary", use_container_width=True):
        with st.spinner("Processing..."):
            try:
                if st.session_state.brand_targets_agg is None:
                    _, st.session_state.brand_targets_agg = map_categories_to_brands(
                        st.session_state.category_targets, st.session_state.historical_df)

                st.session_state.predictions, _ = predict_sku_distribution(
                    st.session_state.brand_targets_agg, st.session_state.historical_df)
                
                if st.session_state.predictions:
                    st.success("🎉 SKU distribution generated! Go to Analysis or Results tab")
                    st.balloons()
                    
            except Exception as e:
                st.error(f"❌ Error: {e}")

with tab2:
    st.header("📊 Analysis")
    if not st.session_state.predictions:
        st.info("📝 Please upload data and generate SKU distribution first")
    else:
        st.write("Analysis features will be implemented here")

with tab3:
    st.header("📋 Results")
    if not st.session_state.predictions:
        st.info("📝 Please upload data and generate SKU distribution first")
    else:
        st.write("Results features will be implemented here")

st.divider()
st.markdown("🏭 **Production Planning App** | 📊 Precise SKU-level production planning")
