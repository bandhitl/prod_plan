import streamlit as st
import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go

# --- Configuration and Constants ---
HISTORICAL_REQUIRED_COLS = ["BRANDPRODUCT", "Item Code", "TON", "Item Name"]

# --- Helper Functions for Data Processing ---

def process_historical_file(uploaded_file):
    """
    Processes the uploaded historical data Excel file.
    Expected structure: Row 1 = title, Row 2 = headers, Row 3+ = data
    """
    try:
        # อ่านไฟล์โดยข้าม row แรก (title) และใช้ row 2 เป็น header
        df = pd.read_excel(uploaded_file, header=1)
        
        st.write("🔍 **ข้อมูลในไฟล์ Historical Data:**")
        st.write(f"จำนวนแถวทั้งหมด: {len(df):,}")
        st.write(f"คอลัมน์ที่พบ: {list(df.columns)}")
        
        # ตรวจสอบคอลัมน์ที่จำเป็น
        missing_cols = [col for col in HISTORICAL_REQUIRED_COLS if col not in df.columns]
        if missing_cols:
            st.error(f"ไฟล์ข้อมูลย้อนหลังขาดคอลัมน์ที่จำเป็น: {', '.join(missing_cols)}")
            return None
        
        # ทำความสะอาดข้อมูล TON
        original_count = len(df)
        df['TON'] = pd.to_numeric(df['TON'], errors='coerce')
        df = df.dropna(subset=['TON'])
        df = df[df['TON'] > 0]  # กรองเฉพาะที่มี TON > 0
        
        st.write(f"📊 **สรุปข้อมูลหลังจากทำความสะอาด:**")
        st.write(f"แถวที่ใช้งานได้: {len(df):,} จาก {original_count:,} แถว")
        
        # สรุปข้อมูลตาม BRANDPRODUCT
        brand_summary = df.groupby('BRANDPRODUCT').agg({
            'Item Code': 'nunique',
            'TON': ['count', 'sum']
        }).round(2)
        brand_summary.columns = ['จำนวน SKU ไม่ซ้ำ', 'จำนวนรายการ', 'รวม TON']
        brand_summary = brand_summary.sort_values('รวม TON', ascending=False)
        
        st.write("**📈 สรุปข้อมูลตาม BRANDPRODUCT:**")
        st.dataframe(brand_summary)
        
        # แสดงตัวอย่างข้อมูล
        st.write("**🔍 ตัวอย่างข้อมูล:**")
        st.dataframe(df[['BRANDPRODUCT', 'Item Code', 'Item Name', 'TON']].head(10))
        
        return df
        
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์ข้อมูลย้อนหลัง: {e}")
        import traceback
        st.error(f"รายละเอียด: {traceback.format_exc()}")
        return None

def process_target_file(uploaded_file):
    """
    Processes the BNI Sales Rolling target file with the specific structure.
    """
    try:
        # อ่านไฟล์โดยไม่กำหนด header
        df = pd.read_excel(uploaded_file, sheet_name=0, header=None)
        
        st.write("🔍 **ข้อมูลในไฟล์ BNI Sales Rolling:**")
        st.dataframe(df.head(10))
        
        # ตรวจสอบโครงสร้างไฟล์
        if len(df) < 3:
            st.error("❌ ไฟล์มีข้อมูลไม่เพียงพอ ต้องมีอย่างน้อย 3 แถว")
            return None
        
        # หาตำแหน่งของคอลัมน์ May และ W1
        may_col_idx = None
        w1_col_idx = None
        
        # ค้นหาในแถวที่ 1 และ 2
        for row_idx in range(min(3, len(df))):
            for col_idx in range(len(df.columns)):
                cell_value = str(df.iloc[row_idx, col_idx]).strip().lower()
                if 'may' in cell_value and may_col_idx is None:
                    may_col_idx = col_idx
                    st.success(f"✅ พบคอลัมน์ 'May' ที่ตำแหน่ง ({row_idx+1}, {col_idx+1})")
                elif 'w1' in cell_value and w1_col_idx is None:
                    w1_col_idx = col_idx
                    st.success(f"✅ พบคอลัมน์ 'W1' ที่ตำแหน่ง ({row_idx+1}, {col_idx+1})")
        
        # หากไม่พบคอลัมน์ ให้ใช้ค่าเริ่มต้น
        if may_col_idx is None:
            may_col_idx = 1
            st.warning(f"⚠️ ไม่พบคอลัมน์ 'May' ใช้ค่าเริ่มต้นคอลัมน์ที่ 2")
        
        if w1_col_idx is None:
            w1_col_idx = 2
            st.warning(f"⚠️ ไม่พบคอลัมน์ 'W1' ใช้ค่าเริ่มต้นคอลัมน์ที่ 3")
        
        # หาแถวเริ่มต้นข้อมูล และแถวสิ้นสุด
        start_row_idx = 2
        end_row_idx = len(df)
        
        for i in range(start_row_idx, len(df)):
            if i < len(df):
                cell_value = str(df.iloc[i, 0]).strip().lower()
                if 'total' in cell_value or 'รวม' in cell_value:
                    end_row_idx = i
                    st.info(f"📍 พบแถว 'Total' ที่แถวที่ {i+1}")
                    break
        
        # แยกข้อมูล category
        category_data = []
        for i in range(start_row_idx, end_row_idx):
            if i < len(df):
                category_name = df.iloc[i, 0]
                may_value = df.iloc[i, may_col_idx] if may_col_idx < len(df.columns) else 0
                w1_value = df.iloc[i, w1_col_idx] if w1_col_idx < len(df.columns) else 0
                
                # ทำความสะอาดข้อมูล
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
        
        # แสดงข้อมูลที่แยกได้
        if category_data:
            st.write(f"📋 **ข้อมูลที่แยกได้ ({len(category_data)} categories):**")
            preview_df = pd.DataFrame(category_data)
            st.dataframe(preview_df)
            
            # แปลงเป็น dictionary format
            category_targets = {}
            for item in category_data:
                category_targets[item['Category']] = {
                    'mayTarget': item['MayTarget'],
                    'w1Target': item['W1Target']
                }
            
            st.success(f"✅ ประมวลผลสำเร็จ! พบ {len(category_targets)} categories")
            return category_targets
        else:
            st.error("❌ ไม่พบข้อมูล category ในไฟล์")
            return None
            
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์เป้าหมาย: {e}")
        import traceback
        st.error(f"รายละเอียด: {traceback.format_exc()}")
        return None

def map_categories_to_historical_brands(category_targets, historical_df):
    """Maps BNI categories to historical brands and aggregates targets."""
    
    # สร้าง summary ของข้อมูลย้อนหลัง
    historical_summary = {}
    if historical_df is not None:
        hist_summary = historical_df.groupby('BRANDPRODUCT')['TON'].sum()
        historical_summary = hist_summary.to_dict()
    
    brand_mapping = {}
    brand_targets_agg = {}

    st.write("🔄 **การจับคู่ Categories กับ Brands:**")
    
    mapping_issues = []
    
    for category, targets in category_targets.items():
        matching_brand = None
        cat_lower = str(category).lower()

        # การจับคู่ที่ปรับปรุงให้เหมาะกับไฟล์จริง
        if 'scg' in cat_lower:
            if 'pipe' in cat_lower or 'conduit' in cat_lower:
                matching_brand = 'SCG-PI'
            elif 'fitting' in cat_lower:
                matching_brand = 'SCG-FT'
            elif 'ball valve' in cat_lower or 'valve' in cat_lower:
                matching_brand = 'SCG-BV'
        elif 'mizu' in cat_lower:
            if 'pipe' in cat_lower or 'conduit' in cat_lower or 'c 5/8' in cat_lower or 'yellow' in cat_lower or 'grey' in cat_lower:
                matching_brand = 'MIZU-PI'
            elif 'fitting' in cat_lower:
                matching_brand = 'MIZU-FT'
        elif any(keyword in cat_lower for keyword in ['icon', 'micon', 'scala']):
            matching_brand = 'ICON-PI'
        elif 'fitting (trading)' in cat_lower or ('fitting' in cat_lower and 'trading' in cat_lower):
            matching_brand = 'SCG-FT'
        elif 'ball valve (trading)' in cat_lower or ('valve' in cat_lower and 'trading' in cat_lower):
            matching_brand = 'SCG-BV'
        elif 'solvent' in cat_lower or 'glue' in cat_lower:
            matching_brand = 'SOLVENT'
            mapping_issues.append(f"⚠️ {category} → {matching_brand}: ไม่มีข้อมูลย้อนหลัง (จะไม่สามารถคำนวณการกระจาย SKU ได้)")
        else:
            matching_brand = category.replace(' ', '-').replace('(', '').replace(')', '').upper()

        brand_mapping[category] = matching_brand
        
        # ตรวจสอบว่ามีข้อมูลย้อนหลังหรือไม่
        has_historical_data = matching_brand in historical_summary
        historical_tonnage = historical_summary.get(matching_brand, 0)
        
        status_icon = "✅" if has_historical_data else "❌"
        st.write(f"   • {category} → {matching_brand} {status_icon}")
        
        if matching_brand and matching_brand != 'SOLVENT':
            if matching_brand not in brand_targets_agg:
                brand_targets_agg[matching_brand] = {
                    'mayTarget': 0,
                    'w1Target': 0,
                    'categories': [],
                    'historicalTonnage': historical_tonnage
                }
            brand_targets_agg[matching_brand]['mayTarget'] += targets['mayTarget']
            brand_targets_agg[matching_brand]['w1Target'] += targets['w1Target']
            brand_targets_agg[matching_brand]['categories'].append(category)
    
    # แสดงผลสรุปและการวิเคราะหื
    if brand_targets_agg:
        st.write("📊 **สรุปเป้าหมายตาม Brand และการเปรียบเทียบ:**")
        
        comparison_data = []
        for brand, targets in brand_targets_agg.items():
            hist_tonnage = targets['historicalTonnage']
            may_ratio = targets['mayTarget'] / hist_tonnage if hist_tonnage > 0 else float('inf')
            w1_ratio = targets['w1Target'] / hist_tonnage if hist_tonnage > 0 else float('inf')
            
            comparison_data.append({
                'Brand': brand,
                'May Target': targets['mayTarget'],
                'W1 Target': targets['w1Target'],
                'Historical': hist_tonnage,
                'May Ratio': f"{may_ratio:.1f}x" if hist_tonnage > 0 else "N/A",
                'W1 Ratio': f"{w1_ratio:.1f}x" if hist_tonnage > 0 else "N/A",
                'Status': '⚠️ สูงมาก' if (may_ratio > 5 or w1_ratio > 5) and hist_tonnage > 0 else 
                         '❌ ไม่มีข้อมูล' if hist_tonnage == 0 else '✅ ปกติ'
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df)
        
        # แสดงกราฟเปรียบเทียบ
        st.write("📈 **กราฟเปรียบเทียบเป้าหมาย vs ข้อมูลย้อนหลัง:**")
        
        # เตรียมข้อมูลสำหรับกราฟ
        brands = [item['Brand'] for item in comparison_data if item['Historical'] > 0]
        historical = [item['Historical'] for item in comparison_data if item['Historical'] > 0]
        may_targets = [item['May Target'] for item in comparison_data if item['Historical'] > 0]
        w1_targets = [item['W1 Target'] for item in comparison_data if item['Historical'] > 0]
        
        if brands:
            fig = go.Figure(data=[
                go.Bar(name='Historical Data', x=brands, y=historical),
                go.Bar(name='May Target', x=brands, y=may_targets),
                go.Bar(name='W1 Target', x=brands, y=w1_targets)
            ])
            fig.update_layout(
                title='เปรียบเทียบเป้าหมาย vs ข้อมูลย้อนหลัง (ตัน)',
                xaxis_title='Brand',
                yaxis_title='ตัน',
                barmode='group'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # แสดงคำเตือนสำหรับเป้าหมายที่ผิดปกติ
        warnings = []
        for item in comparison_data:
            if item['Historical'] == 0:
                warnings.append(f"❌ **{item['Brand']}**: ไม่มีข้อมูลย้อนหลัง - ไม่สามารถคำนวณการกระจาย SKU ได้")
            elif 'สูงมาก' in item['Status']:
                warnings.append(f"⚠️ **{item['Brand']}**: เป้าหมายสูงมาก ({item['May Ratio']}, {item['W1 Ratio']}) - กรุณาตรวจสอบความถูกต้อง")
        
        if warnings:
            st.warning("**คำเตือน:**")
            for warning in warnings:
                st.write(warning)
        
        # แสดงคำแนะนำ
        st.info("**💡 คำแนะนำ:**\n"
                "- เป้าหมายที่เหมาะสมควรอยู่ในช่วง 1-3 เท่าของข้อมูลย้อนหลัง\n"
                "- หากเป้าหมายสูงเกินไป อาจต้องปรับลดหรือเพิ่มข้อมูลย้อนหลัง\n"
                "- Brand ที่ไม่มีข้อมูลย้อนหลังจะไม่สามารถคำนวณการกระจาย SKU ได้")
    
    return brand_mapping, brand_targets_agg

def predict_sku_distribution(brand_targets_agg, historical_df):
    """Predicts SKU distribution based on historical data and new targets."""
    if historical_df is None or historical_df.empty:
        st.error("ข้อมูลย้อนหลังไม่พร้อมใช้งานสำหรับการคาดการณ์")
        return {}, {}

    st.write("📈 **กำลังสร้างการคาดการณ์การกระจาย SKU...**")
    
    # สร้างตารางรวม tonnage ตาม brand, sku และ item name
    brand_sku_tonnage = historical_df.groupby(['BRANDPRODUCT', 'Item Code', 'Item Name'])['TON'].sum().reset_index()
    
    st.write(f"จำนวน SKU ที่ไม่ซ้ำในข้อมูลย้อนหลัง: {len(brand_sku_tonnage):,}")
    
    # สร้าง mapping สำหรับ sku details
    sku_details_map = {}
    for _, row in brand_sku_tonnage.iterrows():
        sku_details_map[row['Item Code']] = {'name': row['Item Name'], 'brand': row['BRANDPRODUCT']}

    # คำนวณ total tonnage ของแต่ละ brand
    brand_total_tonnage = brand_sku_tonnage.groupby('BRANDPRODUCT')['TON'].sum().rename('TotalBrandTon').reset_index()
    
    # รวมข้อมูลและคำนวณ percentage
    brand_sku_percentages = pd.merge(brand_sku_tonnage, brand_total_tonnage, on='BRANDPRODUCT')
    brand_sku_percentages['Percentage'] = brand_sku_percentages['TON'] / brand_sku_percentages['TotalBrandTon']
    
    # สร้างการคาดการณ์
    predictions = {}
    brands_with_no_data = []
    brands_with_high_growth = []
    
    for brand, targets in brand_targets_agg.items():
        may_target_val = targets['mayTarget']
        w1_target_val = targets['w1Target']
        historical_tonnage = targets.get('historicalTonnage', 0)
        
        # หา SKU ที่ตรงกับ brand
        current_brand_skus = brand_sku_percentages[brand_sku_percentages['BRANDPRODUCT'] == brand]
        
        if len(current_brand_skus) == 0:
            brands_with_no_data.append(brand)
            st.warning(f"⚠️ ไม่พบข้อมูลย้อนหลังสำหรับ Brand: {brand}")
            continue
        
        # ตรวจสอบการเติบโต
        if historical_tonnage > 0:
            may_growth = may_target_val / historical_tonnage
            w1_growth = w1_target_val / historical_tonnage
            if may_growth > 5 or w1_growth > 5:
                brands_with_high_growth.append((brand, may_growth, w1_growth))
        
        st.write(f"✅ Brand {brand}: พบ {len(current_brand_skus)} SKU ในข้อมูลย้อนหลัง")
        
        predictions[brand] = {
            'mayTarget': may_target_val,
            'w1Target': w1_target_val,
            'historicalTonnage': historical_tonnage,
            'categories': targets['categories'],
            'mayDistribution': {},
            'w1Distribution': {},
            'skuCount': len(current_brand_skus)
        }
        
        # คำนวณการกระจายสำหรับแต่ละ SKU
        for _, sku_row in current_brand_skus.iterrows():
            sku_code = sku_row['Item Code']
            percentage = sku_row['Percentage']
            item_name = sku_row['Item Name']
            historical_sku_tonnage = sku_row['TON']

            # ใช้ threshold ที่เหมาะสม (0.1% = 0.001)
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
    
    # แสดงสรุปการคาดการณ์
    st.write("📋 **สรุปการคาดการณ์:**")
    prediction_summary = []
    for brand, pred in predictions.items():
        may_skus = len(pred['mayDistribution'])
        w1_skus = len(pred['w1Distribution'])
        historical_tonnage = pred.get('historicalTonnage', 0)
        growth_may = pred['mayTarget'] / historical_tonnage if historical_tonnage > 0 else 0
        growth_w1 = pred['w1Target'] / historical_tonnage if historical_tonnage > 0 else 0
        
        prediction_summary.append({
            'Brand': brand,
            'จำนวน SKU': pred['skuCount'],
            'May Target': pred['mayTarget'],
            'W1 Target': pred['w1Target'],
            'Historical': historical_tonnage,
            'May Growth': f"{growth_may:.1f}x" if historical_tonnage > 0 else "N/A",
            'W1 Growth': f"{growth_w1:.1f}x" if historical_tonnage > 0 else "N/A"
        })
    
    if prediction_summary:
        pred_df = pd.DataFrame(prediction_summary)
        st.dataframe(pred_df)
    
    # แสดงคำเตือน
    if brands_with_no_data:
        st.error(f"❌ **Brands ที่ไม่มีข้อมูลย้อนหลัง:** {', '.join(brands_with_no_data)}")
    
    if brands_with_high_growth:
        st.warning("⚠️ **Brands ที่มีเป้าหมายเติบโตสูง:**")
        for brand, may_growth, w1_growth in brands_with_high_growth:
            st.write(f"   • {brand}: May {may_growth:.1f}x, W1 {w1_growth:.1f}x")
    
    return predictions, sku_details_map

def generate_excel_download(predictions_data, selected_period_key):
    """Generates an Excel file for download from the predictions."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # สร้าง summary sheet
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
        
        # สร้าง sheet สำหรับแต่ละ brand
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
                
                # เพิ่มคอลัมน์ Growth Ratio
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
st.title("🏭 แอปพลิเคชันวางแผนการผลิต")
st.markdown("📊 วิเคราะหืข้อมูลย้อนหลังและเป้าหมายเพื่อสร้างแผนการผลิตระดับ SKU อย่างแม่นยำ")

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

tab1, tab2, tab3 = st.tabs(["1. 📁 อัปโหลดข้อมูล", "2. 📊 การวิเคราะห์", "3. 📋 ผลลัพธ์"])

with tab1:
    st.header("📁 ส่วนอัปโหลดข้อมูล")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. 📈 ข้อมูลย้อนหลัง (Historical Data)")
        st.markdown("""
        **รูปแบบไฟล์ที่รองรับ:**
        - แถวที่ 1: Title/Header  
        - แถวที่ 2: Column names (ต้องมี: BRANDPRODUCT, Item Code, Item Name, TON)
        - แถวที่ 3+: ข้อมูลการขายราย SKU
        """)
        
        historical_file_upload = st.file_uploader(
            "เลือกไฟล์ Excel ข้อมูลย้อนหลัง", 
            type=['xlsx', 'xls'], 
            key="hist_uploader",
            help="ไฟล์ควรมีข้อมูลการขายราย SKU พร้อม BRANDPRODUCT, Item Code, Item Name และ TON"
        )
        
        if historical_file_upload:
            st.session_state.historical_df = process_historical_file(historical_file_upload)
            if st.session_state.historical_df is not None:
                st.success(f"✅ ไฟล์ข้อมูลย้อนหลัง '{historical_file_upload.name}' โหลดสำเร็จ")

    with col2:
        st.subheader("2. 🎯 ข้อมูลเป้าหมาย (Target Data)")
        st.markdown("""
        **รูปแบบไฟล์ BNI Sales Rolling:**
        - แถวที่ 1: Headers (Sale volume, OP, Rolling)
        - แถวที่ 2: Sub-headers (May, W1, W2, W3, W4)  
        - แถวที่ 3+: Categories พร้อมค่าเป้าหมาย
        - แถวสุดท้าย: Total
        """)
        
        target_file_upload = st.file_uploader(
            "เลือกไฟล์ Excel ข้อมูลเป้าหมาย", 
            type=['xlsx', 'xls'], 
            key="target_uploader",
            help="ไฟล์ BNI Sales Rolling ที่มีเป้าหมายรายกลุ่มสินค้า"
        )
        
        if target_file_upload:
            st.session_state.category_targets = process_target_file(target_file_upload)
            if st.session_state.category_targets:
                st.success(f"✅ ไฟล์ข้อมูลเป้าหมาย '{target_file_upload.name}' โหลดสำเร็จ")
                if st.session_state.historical_df is not None:
                    _, st.session_state.brand_targets_agg = map_categories_to_historical_brands(
                        st.session_state.category_targets, 
                        st.session_state.historical_df
                    )

    st.divider()
    
    # ปุ่มสร้างการกระจาย SKU
    generate_disabled = not (st.session_state.historical_df is not None and st.session_state.category_targets is not None)
    
    if st.button(
        "🚀 สร้างการกระจาย SKU (Generate SKU Distribution)", 
        disabled=generate_disabled,
        type="primary"
    ):
        with st.spinner("กำลังประมวลผลและสร้างการคาดการณ์..."):
            if st.session_state.brand_targets_agg is None: 
                _, st.session_state.brand_targets_agg = map_categories_to_historical_brands(
                    st.session_state.category_targets, 
                    st.session_state.historical_df
                )

            if st.session_state.brand_targets_agg:
                st.session_state.predictions, _ = predict_sku_distribution(
                    st.session_state.brand_targets_agg, 
                    st.session_state.historical_df
                )
                st.success("🎉 การสร้างการกระจาย SKU เสร็จสมบูรณ์! กรุณาไปที่แท็บ 'การวิเคราะห์' หรือ 'ผลลัพธ์'")
                if st.session_state.predictions:
                    st.session_state.selected_brand = next(iter(st.session_state.predictions), None)
                    st.balloons()
            else:
                st.error("❌ ไม่สามารถ map categories กับ brands ได้ หรือไม่มีข้อมูล brand targets")

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
        "เลือกช่วงเวลา (Select Period):",
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
        st.warning("ไม่มีข้อมูลการคาดการณ์สำหรับแบรนด์ใดๆ")
        return None

    if st.session_state.selected_brand not in brand_list:
         st.session_state.selected_brand = brand_list[0] if brand_list else None
    
    try:
        current_brand_index = brand_list.index(st.session_state.selected_brand) if st.session_state.selected_brand else 0
    except ValueError:
        current_brand_index = 0
        st.session_state.selected_brand = brand_list[0] if brand_list else None

    st.session_state.selected_brand = st.selectbox(
        "เลือกแบรนด์ (Select Brand):", 
        options=brand_list,
        index=current_brand_index,
        key=widget_key
    )
    return st.session_state.selected_brand

with tab2:
    st.header("📊 การวิเคราะห์ข้อมูล")
    if not st.session_state.predictions:
        st.info("📝 กรุณาอัปโหลดข้อมูลและสร้างการกระจาย SKU ในแท็บ 'อัปโหลดข้อมูล' ก่อน")
    else:
        selected_period_name = create_period_selector("analysis_period_selector")
        
        st.subheader("📈 การกระจายเป้าหมายตามแบรนด์ (Brand Target Distribution)")
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
                    labels={'Tonnage':'ตัน (Tons)'},
                    color='Tonnage',
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(fig_brand_targets, use_container_width=True)

        st.divider()
        st.subheader("🎯 การกระจาย SKU (SKU Distribution)")
        
        col_brand_sel, col_toggle_sku = st.columns([3,1])
        with col_brand_sel:
            selected_brand = create_brand_selector("analysis_brand_selector")
        with col_toggle_sku:
             st.session_state.show_all_skus = st.checkbox("แสดง SKU ทั้งหมด", value=st.session_state.show_all_skus, key="show_all_skus_toggle")

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
                
                # เพิ่มคอลัมน์ Growth Ratio
                if 'Historical Tonnage' in df_sku_dist.columns:
                    df_sku_dist['Growth Ratio'] = (df_sku_dist['Predicted Tonnage'] / df_sku_dist['Historical Tonnage']).round(2)
                    df_sku_dist['Growth Ratio'] = df_sku_dist['Growth Ratio'].replace([float('inf')], 999.0)
                
                display_df_sku = df_sku_dist if st.session_state.show_all_skus else df_sku_dist.head(15)
                
                if not display_df_sku.empty:
                    # แสดงสถิติสรุป
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("จำนวน SKU", len(df_sku_dist))
                    with col2:
                        total_target = df_sku_dist['Predicted Tonnage'].sum()
                        st.metric("เป้าหมายรวม", f"{total_target:.1f} ตัน")
                    with col3:
                        total_historical = df_sku_dist['Historical Tonnage'].sum()
                        st.metric("ย้อนหลังรวม", f"{total_historical:.1f} ตัน")
                    with col4:
                        overall_growth = total_target / total_historical if total_historical > 0 else 0
                        st.metric("การเติบโต", f"{overall_growth:.1f}x")
                    
                    # กราฟแท่ง
                    fig_sku_bar = px.bar(
                        display_df_sku, 
                        y='SKU', 
                        x='Predicted Tonnage', 
                        orientation='h',
                        title=f"การกระจาย SKU สำหรับ {selected_brand} ({selected_period_name})",
                        labels={'Predicted Tonnage':'ตัน (Tons)'}, 
                        hover_data=['Product Name', 'Historical Tonnage', 'Growth Ratio'],
                        color='Growth Ratio',
                        color_continuous_scale='RdYlGn_r'
                    )
                    fig_sku_bar.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
                    st.plotly_chart(fig_sku_bar, use_container_width=True)

                    # กราฟวงกลม (Top 10)
                    top_n_pie = 8
                    df_pie_data = df_sku_dist.head(top_n_pie).copy()
                    if len(df_sku_dist) > top_n_pie:
                        others_tonnage = df_sku_dist.iloc[top_n_pie:]['Predicted Tonnage'].sum()
                        if others_tonnage > 0.01:
                            others_row = pd.DataFrame([{
                                'SKU': 'Others', 
                                'Product Name': f'อื่นๆ ({len(df_sku_dist) - top_n_pie} SKU)', 
                                'Predicted Tonnage': others_tonnage, 
                                'Percentage': 0.0
                            }])
                            df_pie_data = pd.concat([df_pie_data, others_row], ignore_index=True)

                    fig_sku_pie = px.pie(
                        df_pie_data, 
                        values='Predicted Tonnage', 
                        names='SKU', 
                        title=f"สัดส่วน Top SKU สำหรับ {selected_brand} ({selected_period_name})", 
                        hover_data=['Product Name']
                    )
                    st.plotly_chart(fig_sku_pie, use_container_width=True)
                    
                    # แสดงตารางข้อมูล
                    st.subheader("📋 รายละเอียด SKU")
                    display_columns = ['SKU', 'Product Name', 'Predicted Tonnage', 'Historical Tonnage', 'Growth Ratio', 'Percentage']
                    display_table = display_df_sku[display_columns].copy()
                    display_table['Predicted Tonnage'] = display_table['Predicted Tonnage'].round(3)
                    display_table['Historical Tonnage'] = display_table['Historical Tonnage'].round(3)
                    display_table['Percentage'] = (display_table['Percentage'] * 100).round(2)
                    
                    st.dataframe(display_table, use_container_width=True)
            else:
                st.warning(f"ไม่มีข้อมูลการกระจาย SKU สำหรับ {selected_brand} ในช่วง {selected_period_name}")

with tab3:
    st.header("📋 ผลลัพธ์แผนการผลิต")
    if not st.session_state.predictions:
        st.info("📝 กรุณาอัปโหลดข้อมูลและสร้างการกระจาย SKU ในแท็บ 'อัปโหลดข้อมูล' ก่อน")
    else:
        selected_period_name_results = create_period_selector("results_period_selector")
        selected_brand_res = create_brand_selector("results_brand_selector")

        if selected_brand_res:
            brand_data_res = st.session_state.predictions.get(selected_brand_res)
            dist_key_res = 'mayDistribution' if st.session_state.selected_period == 'may' else 'w1Distribution'
            sku_distribution_res = brand_data_res.get(dist_key_res)

            if sku_distribution_res:
                st.subheader(f"📊 แผนการผลิต {selected_brand_res} - {selected_period_name_results}")
                
                df_results = pd.DataFrame.from_dict(sku_distribution_res, orient='index').reset_index()
                df_results.rename(columns={
                    'index': 'รหัส SKU', 
                    'itemName': 'ชื่อสินค้า', 
                    'tonnage': 'แผนการผลิต (ตัน)', 
                    'percentage': 'สัดส่วน (%)',
                    'historicalTonnage': 'ข้อมูลย้อนหลัง (ตัน)'
                }, inplace=True)
                
                # คำนวณ Growth Ratio
                df_results['อัตราการเติบโต'] = (df_results['แผนการผลิต (ตัน)'] / df_results['ข้อมูลย้อนหลัง (ตัน)']).round(2)
                df_results['อัตราการเติบโต'] = df_results['อัตราการเติบโต'].replace([float('inf')], 999.0)
                
                # จัดรูปแบบข้อมูล
                df_results['สัดส่วน (%)'] = (df_results['สัดส่วน (%)'] * 100).round(2)
                df_results['แผนการผลิต (ตัน)'] = df_results['แผนการผลิต (ตัน)'].round(3)
                df_results['ข้อมูลย้อนหลัง (ตัน)'] = df_results['ข้อมูลย้อนหลัง (ตัน)'].round(3)
                
                # เรียงลำดับตามแผนการผลิต
                df_results = df_results.sort_values(by='แผนการผลิต (ตัน)', ascending=False)
                
                # แสดงสถิติสรุป
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("🎯 เป้าหมายรวม", f"{df_results['แผนการผลิต (ตัน)'].sum():.1f} ตัน")
                with col2:
                    st.metric("📈 ข้อมูลย้อนหลัง", f"{df_results['ข้อมูลย้อนหลัง (ตัน)'].sum():.1f} ตัน")
                with col3:
                    total_growth = df_results['แผนการผลิต (ตัน)'].sum() / df_results['ข้อมูลย้อนหลัง (ตัน)'].sum()
                    st.metric("📊 การเติบโตรวม", f"{total_growth:.1f}x")
                with col4:
                    st.metric("🔢 จำนวน SKU", len(df_results))
                
                # กรองข้อมูลตามเกณฑ์
                filter_option = st.selectbox(
                    "กรองข้อมูล:",
                    ["ทั้งหมด", "แผนการผลิต > 1 ตัน", "แผนการผลิต > 0.5 ตัน", "การเติบโต > 3x", "Top 20 SKU"]
                )
                
                if filter_option == "แผนการผลิต > 1 ตัน":
                    df_display = df_results[df_results['แผนการผลิต (ตัน)'] > 1]
                elif filter_option == "แผนการผลิต > 0.5 ตัน":
                    df_display = df_results[df_results['แผนการผลิต (ตัน)'] > 0.5]
                elif filter_option == "การเติบโต > 3x":
                    df_display = df_results[df_results['อัตราการเติบโต'] > 3]
                elif filter_option == "Top 20 SKU":
                    df_display = df_results.head(20)
                else:
                    df_display = df_results
                
                # แสดงตาราง
                st.dataframe(
                    df_display[['รหัส SKU', 'ชื่อสินค้า', 'แผนการผลิต (ตัน)', 'ข้อมูลย้อนหลัง (ตัน)', 'อัตราการเติบโต', 'สัดส่วน (%)']],
                    use_container_width=True,
                    height=400
                )
                
                # แสดงคำเตือนสำหรับ SKU ที่มีการเติบโตสูง
                high_growth_skus = df_results[df_results['อัตราการเติบโต'] > 5]
                if len(high_growth_skus) > 0:
                    st.warning(f"⚠️ **พบ SKU ที่มีการเติบโตสูงมาก ({len(high_growth_skus)} รายการ):**")
                    st.dataframe(
                        high_growth_skus[['รหัส SKU', 'ชื่อสินค้า', 'แผนการผลิต (ตัน)', 'อัตราการเติบโต']].head(10),
                        use_container_width=True
                    )
            else:
                st.warning(f"ไม่มีข้อมูลผลลัพธ์สำหรับ {selected_brand_res}")

        # ส่วนดาวน์โหลด Excel
        if st.session_state.predictions:
            st.divider()
            st.subheader("📥 ดาวน์โหลดผลลัพธ์")
            
            col_download1, col_download2 = st.columns(2)
            
            with col_download1:
                excel_bytes = generate_excel_download(st.session_state.predictions, st.session_state.selected_period)
                st.download_button(
                    label="📊 ดาวน์โหลดผลลัพธ์ทั้งหมดเป็น Excel",
                    data=excel_bytes,
                    file_name=f"production_plan_{st.session_state.selected_period}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
            
            with col_download2:
                st.info("**ไฟล์ Excel จะประกอบด้วย:**\n"
                       "- Summary: สรุปรวมทุก Brand\n"  
                       "- แต่ละ Brand: รายละเอียด SKU พร้อมการเปรียบเทียบ\n"
                       "- Growth Ratio: อัตราการเติบโตของแต่ละ SKU")

# เพิ่ม footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>🏭 <strong>Production Planning App</strong> | 
    📊 วิเคราะหืข้อมูลย้อนหลังเพื่อคาดการณ์การผลิต | 
    🎯 แผนการผลิตระดับ SKU ที่แม่นยำ</p>
</div>
""", unsafe_allow_html=True)
