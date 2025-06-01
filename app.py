import streamlit as st
import pandas as pd
import io
import plotly.express as px

# --- Configuration and Constants ---
HISTORICAL_REQUIRED_COLS = ["BRANDPRODUCT", "Item Code", "TON", "Item Name"]

# --- Helper Functions for Data Processing ---

def process_historical_file(uploaded_file):
    """Processes the uploaded historical data Excel file."""
    try:
        df = pd.read_excel(uploaded_file, header=1)
        missing_cols = [col for col in HISTORICAL_REQUIRED_COLS if col not in df.columns]
        if missing_cols:
            st.error(f"ไฟล์ข้อมูลย้อนหลังขาดคอลัมน์ที่จำเป็น: {', '.join(missing_cols)}")
            return None
        df['TON'] = pd.to_numeric(df['TON'], errors='coerce')
        df.dropna(subset=['TON'], inplace=True)
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์ข้อมูลย้อนหลัง: {e}")
        return None

def process_target_file(uploaded_file):
    """
    Processes the BNI Sales Rolling target file with the specific structure:
    Row 1: Headers with "May" and "W1" etc.
    Row 2: Sub-headers 
    Row 3+: Category data with tonnage values
    Last row: Total
    """
    try:
        # อ่านไฟล์โดยไม่กำหนด header
        df = pd.read_excel(uploaded_file, sheet_name=0, header=None)
        
        st.write("🔍 **ข้อมูลในไฟล์ Excel:**")
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
                if 'may' in cell_value:
                    may_col_idx = col_idx
                    st.success(f"✅ พบคอลัมน์ 'May' ที่ตำแหน่ง ({row_idx+1}, {col_idx+1})")
                elif 'w1' in cell_value:
                    w1_col_idx = col_idx
                    st.success(f"✅ พบคอลัมน์ 'W1' ที่ตำแหน่ง ({row_idx+1}, {col_idx+1})")
        
        # หากไม่พบคอลัมน์ ให้ใช้ค่าเริ่มต้น
        if may_col_idx is None:
            may_col_idx = 1  # คอลัมน์ที่ 2 (index 1)
            st.warning(f"⚠️ ไม่พบคอลัมน์ 'May' ใช้ค่าเริ่มต้นคอลัมน์ที่ 2")
        
        if w1_col_idx is None:
            w1_col_idx = 2  # คอลัมน์ที่ 3 (index 2)
            st.warning(f"⚠️ ไม่พบคอลัมน์ 'W1' ใช้ค่าเริ่มต้นคอลัมน์ที่ 3")
        
        # หาแถวเริ่มต้นข้อมูล (ข้าม header)
        start_row_idx = 2  # เริ่มจากแถวที่ 3 (index 2)
        
        # หาแถวสิ้นสุด (Total)
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
                    # แปลงค่าเป็นตัวเลข
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
            
            # แปลงเป็น dictionary format ที่โปรแกรมต้องการ
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


def map_categories_to_historical_brands(category_targets):
    """Maps BNI categories to historical brands and aggregates targets."""
    brand_mapping = {}
    brand_targets_agg = {}

    st.write("🔄 **การจับคู่ Categories กับ Brands:**")
    
    for category, targets in category_targets.items():
        matching_brand = None
        cat_lower = str(category).lower()

        # การจับคู่ที่ปรับปรุงให้เหมาะกับไฟล์ BNI Sales Rolling
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
        elif 'fitting (trading)' in cat_lower or 'fitting' in cat_lower and 'trading' in cat_lower:
            matching_brand = 'SCG-FT'
        elif 'ball valve (trading)' in cat_lower or ('valve' in cat_lower and 'trading' in cat_lower):
            matching_brand = 'SCG-BV'
        elif 'solvent' in cat_lower or 'glue' in cat_lower:
            matching_brand = 'SOLVENT'  # เปลี่ยนจาก '-' เป็น 'SOLVENT' เพื่อให้ติดตาม
        else:
            # หากไม่ตรงกับเงื่อนไขใดๆ ให้สร้าง brand ใหม่จากชื่อ category
            matching_brand = category.replace(' ', '-').replace('(', '').replace(')', '').upper()

        brand_mapping[category] = matching_brand
        st.write(f"   • {category} → {matching_brand}")

        if matching_brand and matching_brand != '-':
            if matching_brand not in brand_targets_agg:
                brand_targets_agg[matching_brand] = {
                    'mayTarget': 0,
                    'w1Target': 0,
                    'categories': []
                }
            brand_targets_agg[matching_brand]['mayTarget'] += targets['mayTarget']
            brand_targets_agg[matching_brand]['w1Target'] += targets['w1Target']
            brand_targets_agg[matching_brand]['categories'].append(category)
    
    # แสดงผลสรุป
    if brand_targets_agg:
        st.write("📊 **สรุปเป้าหมายตาม Brand:**")
        summary_data = []
        for brand, targets in brand_targets_agg.items():
            summary_data.append({
                'Brand': brand,
                'May Target': targets['mayTarget'],
                'W1 Target': targets['w1Target'],
                'Categories Count': len(targets['categories'])
            })
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df)
            
    return brand_mapping, brand_targets_agg

def predict_sku_distribution(brand_targets_agg, historical_df):
    """Predicts SKU distribution based on historical data and new targets."""
    if historical_df is None or historical_df.empty:
        st.error("ข้อมูลย้อนหลังไม่พร้อมใช้งานสำหรับการคาดการณ์")
        return {}, {}

    brand_sku_tonnage = historical_df.groupby(['BRANDPRODUCT', 'Item Code', 'Item Name'])['TON'].sum().reset_index()
    
    sku_details_map = {}
    for _, row in brand_sku_tonnage.iterrows():
        sku_details_map[row['Item Code']] = {'name': row['Item Name'], 'brand': row['BRANDPRODUCT']}

    brand_total_tonnage = brand_sku_tonnage.groupby('BRANDPRODUCT')['TON'].sum().rename('TotalBrandTon').reset_index()
    
    brand_sku_percentages = pd.merge(brand_sku_tonnage, brand_total_tonnage, on='BRANDPRODUCT')
    brand_sku_percentages['Percentage'] = brand_sku_percentages['TON'] / brand_sku_percentages['TotalBrandTon']
    
    predictions = {}
    for brand, targets in brand_targets_agg.items():
        may_target_val = targets['mayTarget']
        w1_target_val = targets['w1Target']
        
        current_brand_skus = brand_sku_percentages[brand_sku_percentages['BRANDPRODUCT'] == brand]
        
        predictions[brand] = {
            'mayTarget': may_target_val,
            'w1Target': w1_target_val,
            'categories': targets['categories'],
            'mayDistribution': {},
            'w1Distribution': {}
        }
        
        for _, sku_row in current_brand_skus.iterrows():
            sku_code = sku_row['Item Code']
            percentage = sku_row['Percentage']
            item_name = sku_row['Item Name']

            if percentage >= 0.001:
                predicted_tonnage_may = may_target_val * percentage
                predictions[brand]['mayDistribution'][sku_code] = {
                    'tonnage': predicted_tonnage_may,
                    'percentage': percentage,
                    'itemName': item_name
                }
                predicted_tonnage_w1 = w1_target_val * percentage
                predictions[brand]['w1Distribution'][sku_code] = {
                    'tonnage': predicted_tonnage_w1,
                    'percentage': percentage,
                    'itemName': item_name
                }
    return predictions, sku_details_map


def generate_excel_download(predictions_data, selected_period_key):
    """
    Generates an Excel file for download from the predictions.
    This is a robust version that handles column names safely.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for brand, data in predictions_data.items():
            period_dist_key = 'mayDistribution' if selected_period_key == 'may' else 'w1Distribution'
            dist_data = data.get(period_dist_key)

            if dist_data:
                df_dist = pd.DataFrame.from_dict(dist_data, orient='index').reset_index()
                
                rename_map = {
                    'index': 'SKU',
                    'itemName': 'Product Name',
                    'tonnage': 'Tonnage',
                    'percentage': 'Percentage'
                }
                
                df_dist.rename(columns=rename_map, inplace=True)
                
                if 'Percentage' in df_dist.columns:
                    df_dist['Percentage'] = (df_dist['Percentage'] * 100).round(2)
                
                df_dist = df_dist.sort_values(by='Tonnage', ascending=False)
                
                final_columns_order = ['SKU', 'Product Name', 'Tonnage', 'Percentage']
                
                output_df = df_dist.reindex(columns=final_columns_order)
                
                sheet_name = brand.replace('/', '-').replace('\\', '-')
                sheet_name = sheet_name[:31]
                
                output_df.to_excel(writer, index=False, sheet_name=sheet_name)
    
    processed_data = output.getvalue()
    return processed_data

# --- Streamlit App UI ---
st.set_page_config(layout="wide", page_title="Production Planning App")
st.title("แอปพลิเคชันวางแผนการผลิต")
st.markdown("อัปโหลดข้อมูลย้อนหลังและไฟล์เป้าหมายเพื่อสร้างแผนการผลิตระดับ SKU")

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


tab1, tab2, tab3 = st.tabs(["1. อัปโหลดข้อมูล (Upload Data)", "2. การวิเคราะห์ (Analysis)", "3. ผลลัพธ์ (Results)"])

with tab1:
    st.header("ส่วนอัปโหลดข้อมูล")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. อัปโหลดข้อมูลย้อนหลัง (Historical Data)")
        st.markdown("ไฟล์นี้ควรมีข้อมูลยอดขายย้อนหลังระดับ SKU พร้อมคอลัมน์สำหรับ Brand, SKU, Tonnage และ Item Name (ชื่อสินค้า)")
        historical_file_upload = st.file_uploader("เลือกไฟล์ Excel ข้อมูลย้อนหลัง", type=['xlsx', 'xls'], key="hist_uploader")
        if historical_file_upload:
            st.session_state.historical_df = process_historical_file(historical_file_upload)
            if st.session_state.historical_df is not None:
                st.success(f"ไฟล์ข้อมูลย้อนหลัง '{historical_file_upload.name}' โหลดสำเร็จแล้ว มี {len(st.session_state.historical_df)} แถว")

    with col2:
        st.subheader("2. อัปโหลดข้อมูลเป้าหมาย (Target Data)")
        st.markdown("อัปโหลดไฟล์ **BNI Sales Rolling** ที่มีโครงสร้าง: แถวแรกมี headers (May, W1), แถวต่อไปเป็นข้อมูล categories พร้อมค่าเป้าหมาย")
        target_file_upload = st.file_uploader("เลือกไฟล์ Excel ข้อมูลเป้าหมาย", type=['xlsx', 'xls'], key="target_uploader")
        if target_file_upload:
            st.session_state.category_targets = process_target_file(target_file_upload)
            if st.session_state.category_targets:
                st.success(f"ไฟล์ข้อมูลเป้าหมาย '{target_file_upload.name}' โหลดสำเร็จแล้ว มี {len(st.session_state.category_targets)} categories")
                if st.session_state.historical_df is not None:
                    _, st.session_state.brand_targets_agg = map_categories_to_historical_brands(st.session_state.category_targets)

    if st.button("สร้างการกระจาย SKU (Generate SKU Distribution)", disabled=not (st.session_state.historical_df is not None and st.session_state.category_targets is not None)):
        with st.spinner("กำลังประมวลผลและสร้างการคาดการณ์..."):
            if st.session_state.brand_targets_agg is None: 
                 _, st.session_state.brand_targets_agg = map_categories_to_historical_brands(st.session_state.category_targets)

            if st.session_state.brand_targets_agg:
                st.session_state.predictions, _ = predict_sku_distribution(
                    st.session_state.brand_targets_agg, 
                    st.session_state.historical_df
                )
                st.success("การสร้างการกระจาย SKU เสร็จสมบูรณ์! กรุณาไปที่แท็บ 'Analysis' หรือ 'Results'")
                if st.session_state.predictions:
                    st.session_state.selected_brand = next(iter(st.session_state.predictions), None)
            else:
                st.error("ไม่สามารถ map categories กับ brands ได้ หรือไม่มีข้อมูล brand targets")

# --- Common period selector logic ---
def create_period_selector(widget_key):
    period_options = {'may': 'May', 'w1': 'Week 1'}
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

# --- Common brand selector logic ---
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
    st.header("การวิเคราะห์ข้อมูล")
    if not st.session_state.predictions:
        st.info("กรุณาอัปโหลดข้อมูลและสร้างการกระจาย SKU ในแท็บ 'Upload Data' ก่อน")
    else:
        selected_period_name = create_period_selector("analysis_period_selector")
        
        st.subheader("การกระจายเป้าหมายตามแบรนด์ (Brand Target Distribution)")
        if st.session_state.brand_targets_agg:
            brand_target_data = []
            target_key = 'mayTarget' if st.session_state.selected_period == 'may' else 'w1Target'
            for brand, targets in st.session_state.brand_targets_agg.items():
                if targets[target_key] > 0:
                    brand_target_data.append({'Brand': brand, 'Tonnage': targets[target_key]})
            
            if brand_target_data:
                df_brand_targets = pd.DataFrame(brand_target_data)
                fig_brand_targets = px.bar(df_brand_targets, x='Brand', y='Tonnage', title=f"Brand Targets for {selected_period_name}",
                                           labels={'Tonnage':'Tonnage (Tons)'})
                st.plotly_chart(fig_brand_targets, use_container_width=True)

        st.divider()
        st.subheader("การกระจาย SKU (SKU Distribution)")
        
        col_brand_sel, col_toggle_sku = st.columns([3,1])
        with col_brand_sel:
            selected_brand = create_brand_selector("analysis_brand_selector")
        with col_toggle_sku:
             st.session_state.show_all_skus = st.checkbox("แสดง SKU ทั้งหมด (Show All SKUs)", value=st.session_state.show_all_skus, key="show_all_skus_toggle")

        if selected_brand:
            brand_data = st.session_state.predictions.get(selected_brand)
            dist_key = 'mayDistribution' if st.session_state.selected_period == 'may' else 'w1Distribution'
            sku_distribution = brand_data.get(dist_key)

            if sku_distribution:
                df_sku_dist = pd.DataFrame.from_dict(sku_distribution, orient='index').reset_index()
                df_sku_dist.rename(columns={'index': 'SKU', 'itemName': 'Product Name', 'tonnage': 'Tonnage', 'percentage': 'percentage'}, inplace=True)
                df_sku_dist = df_sku_dist.sort_values(by='Tonnage', ascending=False)
                
                display_df_sku = df_sku_dist if st.session_state.show_all_skus else df_sku_dist.head(10)
                
                if not display_df_sku.empty:
                    fig_sku_bar = px.bar(display_df_sku, y='SKU', x='Tonnage', orientation='h',
                                         title=f"SKU Distribution for {selected_brand} ({selected_period_name})",
                                         labels={'Tonnage':'Tonnage (Tons)'}, hover_data=['Product Name'])
                    fig_sku_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_sku_bar, use_container_width=True)

                    top_n_pie = 5
                    df_pie_data = df_sku_dist.head(top_n_pie).copy()
                    if len(df_sku_dist) > top_n_pie:
                        others_tonnage = df_sku_dist.iloc[top_n_pie:]['Tonnage'].sum()
                        if others_tonnage > 0.01:
                            others_row = pd.DataFrame([{
                                'SKU': 'Others', 
                                'Product Name': 'Other SKUs', 
                                'Tonnage': others_tonnage, 
                                'percentage': 0.0
                            }])
                            df_pie_data = pd.concat([df_pie_data, others_row], ignore_index=True)

                    fig_sku_pie = px.pie(df_pie_data, values='Tonnage', names='SKU', 
                                         title=f"Top SKUs for {selected_brand} ({selected_period_name})", hover_data=['Product Name'])
                    st.plotly_chart(fig_sku_pie, use_container_width=True)

with tab3:
    st.header("ผลลัพธ์แผนการผลิต")
    if not st.session_state.predictions:
        st.info("กรุณาอัปโหลดข้อมูลและสร้างการกระจาย SKU ในแท็บ 'Upload Data' ก่อน")
    else:
        create_period_selector("results_period_selector")
        selected_brand_res = create_brand_selector("results_brand_selector")

        if selected_brand_res:
            brand_data_res = st.session_state.predictions.get(selected_brand_res)
            dist_key_res = 'mayDistribution' if st.session_state.selected_period == 'may' else 'w1Distribution'
            sku_distribution_res = brand_data_res.get(dist_key_res)

            if sku_distribution_res:
                df_results = pd.DataFrame.from_dict(sku_distribution_res, orient='index').reset_index()
                df_results.rename(columns={'index': 'SKU', 'itemName': 'Product Name', 'tonnage': 'Tonnage', 'percentage': 'Percentage'}, inplace=True)
                df_results['Percentage'] = (df_results['Percentage'] * 100).round(2).astype(str) + '%'
                df_results['Tonnage'] = df_results['Tonnage'].round(4)
                df_results = df_results[['SKU', 'Product Name', 'Tonnage', 'Percentage']].sort_values(by='Tonnage', ascending=False)
                
                st.dataframe(df_results, use_container_width=True)

        if st.session_state.predictions:
            excel_bytes = generate_excel_download(st.session_state.predictions, st.session_state.selected_period)
            st.download_button(
                label="ดาวน์โหลดผลลัพธ์ทั้งหมดเป็น Excel (Download All Results as Excel)",
                data=excel_bytes,
                file_name=f"production_plan_{st.session_state.selected_period}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
