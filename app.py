import streamlit as st
import pandas as pd
import io
import plotly.express as px

# --- Configuration and Constants ---
HISTORICAL_REQUIRED_COLS = ["BRANDPRODUCT", "Item Code", "TON", "Item Name"]
TARGET_CATEGORY_COL = 0
TARGET_MAY_COL = 1
TARGET_W1_COL = 2

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
    Processes the uploaded target data Excel file.
    This version is more flexible and searches for the 'Category' header row.
    """
    try:
        df = pd.read_excel(uploaded_file, sheet_name=0, header=None)
        
        header_row_idx = -1
        # Find the row index where the header 'Category' is located
        for i, row in df.iterrows():
            if str(row.iloc[TARGET_CATEGORY_COL]).strip() == 'Category':
                header_row_idx = i
                break
        
        if header_row_idx == -1:
            st.error("ไม่พบแถวหัวข้อ 'Category' ในไฟล์เป้าหมาย กรุณาตรวจสอบไฟล์")
            return None
            
        start_row_idx = header_row_idx + 1
        end_row_idx = len(df)

        # Find the end row (before "Total")
        for i in range(start_row_idx, len(df)):
            if str(df.iloc[i, TARGET_CATEGORY_COL]).strip() == 'Total':
                end_row_idx = i
                break
        
        target_data_df = df.iloc[start_row_idx:end_row_idx, [TARGET_CATEGORY_COL, TARGET_MAY_COL, TARGET_W1_COL]]
        target_data_df.columns = ['Category', 'MayTarget', 'W1Target']

        target_data_df['MayTarget'] = pd.to_numeric(target_data_df['MayTarget'], errors='coerce').fillna(0)
        target_data_df['W1Target'] = pd.to_numeric(target_data_df['W1Target'], errors='coerce').fillna(0)
        
        category_targets = {}
        for _, row in target_data_df.iterrows():
            if pd.notna(row['Category']) and row['Category'].strip() != '':
                category_targets[row['Category']] = {
                    'mayTarget': row['MayTarget'],
                    'w1Target': row['W1Target']
                }
        return category_targets
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์เป้าหมาย: {e}")
        return None


def map_categories_to_historical_brands(category_targets):
    """Maps BNI categories to historical brands and aggregates targets."""
    brand_mapping = {}
    brand_targets_agg = {}

    for category, targets in category_targets.items():
        matching_brand = None
        cat_lower = str(category).lower() # Ensure category is string and lowercased for matching

        if 'scg' in cat_lower:
            if 'pipe' in cat_lower or 'conduit' in cat_lower:
                matching_brand = 'SCG-PI'
            elif 'fitting' in cat_lower:
                matching_brand = 'SCG-FT'
            elif 'ball valve' in cat_lower:
                matching_brand = 'SCG-BV'
        elif 'mizu' in cat_lower:
            if 'pipe' in cat_lower or 'conduit' in cat_lower or 'c 5/8' in cat_lower:
                matching_brand = 'MIZU-PI'
            elif 'fitting' in cat_lower:
                matching_brand = 'MIZU-FT'
        elif any(keyword in cat_lower for keyword in ['icon', 'micon', 'scala']):
            matching_brand = 'ICON-PI'
        elif 'fitting (trading)' in cat_lower:
            matching_brand = 'SCG-FT'
        elif 'ball valve (trading)' in cat_lower:
            matching_brand = 'SCG-BV'
        elif 'solvent' in cat_lower or 'glue' in cat_lower:
            matching_brand = '-' # Skip or handle as per original logic

        brand_mapping[category] = matching_brand

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

            if percentage >= 0.001: # Only include SKUs with > 0.1% contribution
                # May Distribution
                predicted_tonnage_may = may_target_val * percentage
                predictions[brand]['mayDistribution'][sku_code] = {
                    'tonnage': predicted_tonnage_may,
                    'percentage': percentage,
                    'itemName': item_name
                }
                # W1 Distribution
                predicted_tonnage_w1 = w1_target_val * percentage
                predictions[brand]['w1Distribution'][sku_code] = {
                    'tonnage': predicted_tonnage_w1,
                    'percentage': percentage,
                    'itemName': item_name
                }
    return predictions, sku_details_map


def generate_excel_download(predictions_data, selected_period_key):
    """Generates an Excel file for download from the predictions."""
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='openpyxl')
    
    all_data_frames = []

    for brand, data in predictions_data.items():
        period_target_key = 'mayTarget' if selected_period_key == 'may' else 'w1Target'
        period_dist_key = 'mayDistribution' if selected_period_key == 'may' else 'w1Distribution'
        
        brand_info = pd.DataFrame({
            'ข้อมูล': ['Brand', 'Target (Tons)', 'Period', 'Categories'],
            'รายละเอียด': [
                brand, 
                data[period_target_key],
                'May' if selected_period_key == 'may' else 'Week 1',
                ', '.join(data['categories'])
            ]
        })
        all_data_frames.append(brand_info)
        all_data_frames.append(pd.DataFrame()) # Blank row

        dist_data = data[period_dist_key]
        if dist_data:
            df_dist = pd.DataFrame.from_dict(dist_data, orient='index')
            df_dist.index.name = 'SKU'
            df_dist.reset_index(inplace=True)
            df_dist = df_dist[['SKU', 'itemName', 'tonnage', 'percentage']]
            df_dist.columns = ['SKU', 'Product Name', 'Tonnage (Tons)', 'Percentage (%)']
            df_dist['Percentage (%)'] = df_dist['Percentage (%)'] * 100
            df_dist = df_dist.sort_values(by='Tonnage (Tons)', ascending=False)
            all_data_frames.append(df_dist)
        else:
            all_data_frames.append(pd.DataFrame({'Message': [f"No SKU distribution data for {brand} in this period."]}))
        
        all_data_frames.append(pd.DataFrame()) # Blank row
        all_data_frames.append(pd.DataFrame()) # Another blank row

    if all_data_frames:
        final_df = pd.concat(all_data_frames, ignore_index=True)
        final_df.to_excel(writer, index=False, sheet_name=f"Production Plan - {'May' if selected_period_key == 'may' else 'W1'}")
    
    writer.close()
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
if 'sku_details_map' not in st.session_state:
    st.session_state.sku_details_map = None
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Upload Data"
if 'selected_period' not in st.session_state:
    st.session_state.selected_period = 'may' # 'may' or 'w1'
if 'selected_brand_analysis' not in st.session_state:
    st.session_state.selected_brand_analysis = None
if 'selected_brand_results' not in st.session_state:
    st.session_state.selected_brand_results = None
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
        st.markdown("อัปโหลดไฟล์ BNI Sales Rolling ของคุณพร้อมเป้าหมายระดับแบรนด์ (หรือ Category ที่จะถูก map ไปยัง Brand)")
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
                st.session_state.predictions, st.session_state.sku_details_map = predict_sku_distribution(
                    st.session_state.brand_targets_agg, 
                    st.session_state.historical_df
                )
                st.success("การสร้างการกระจาย SKU เสร็จสมบูรณ์! กรุณาไปที่แท็บ 'Analysis' หรือ 'Results'")
                if st.session_state.predictions:
                    first_brand = next(iter(st.session_state.predictions), None)
                    st.session_state.selected_brand_analysis = first_brand
                    st.session_state.selected_brand_results = first_brand
            else:
                st.error("ไม่สามารถ map categories กับ brands ได้ หรือไม่มีข้อมูล brand targets")


with tab2:
    st.header("การวิเคราะห์ข้อมูล")
    if not st.session_state.predictions:
        st.info("กรุณาอัปโหลดข้อมูลและสร้างการกระจาย SKU ในแท็บ 'Upload Data' ก่อน")
    else:
        period_options = {'may': 'May', 'w1': 'Week 1'}
        st.session_state.selected_period = st.radio(
            "เลือกช่วงเวลา (Select Period):",
            options=list(period_options.keys()),
            format_func=lambda x: period_options[x],
            horizontal=True,
            key="analysis_period_selector"
        )
        
        st.subheader("การกระจายเป้าหมายตามแบรนด์ (Brand Target Distribution)")
        if st.session_state.brand_targets_agg:
            brand_target_data = []
            target_key = 'mayTarget' if st.session_state.selected_period == 'may' else 'w1Target'
            for brand, targets in st.session_state.brand_targets_agg.items():
                if targets[target_key] > 0 :
                    brand_target_data.append({'Brand': brand, 'Tonnage': targets[target_key]})
            
            if brand_target_data:
                df_brand_targets = pd.DataFrame(brand_target_data)
                fig_brand_targets = px.bar(df_brand_targets, x='Brand', y='Tonnage', title=f"Brand Targets for {period_options[st.session_state.selected_period]}",
                                           labels={'Tonnage':'Tonnage (Tons)'})
                st.plotly_chart(fig_brand_targets, use_container_width=True)
            else:
                st.info(f"ไม่มีข้อมูลเป้าหมายแบรนด์สำหรับช่วงเวลา {period_options[st.session_state.selected_period]}")

        st.divider()
        st.subheader("การกระจาย SKU (SKU Distribution)")
        
        brand_list = list(st.session_state.predictions.keys())
        if not brand_list:
            st.warning("ไม่มีข้อมูลการคาดการณ์สำหรับแบรนด์ใดๆ")
        else:
            if st.session_state.selected_brand_analysis not in brand_list:
                 st.session_state.selected_brand_analysis = brand_list[0] if brand_list else None

            col_brand_sel, col_toggle_sku = st.columns([3,1])
            with col_brand_sel:
                st.session_state.selected_brand_analysis = st.selectbox(
                    "เลือกแบรนด์ (Select Brand):", 
                    options=brand_list, 
                    index=brand_list.index(st.session_state.selected_brand_analysis) if st.session_state.selected_brand_analysis in brand_list else 0,
                    key="analysis_brand_selector"
                )
            with col_toggle_sku:
                 st.session_state.show_all_skus = st.checkbox("แสดง SKU ทั้งหมด (Show All SKUs)", value=st.session_state.show_all_skus, key="show_all_skus_toggle")


            if st.session_state.selected_brand_analysis:
                brand_data = st.session_state.predictions.get(st.session_state.selected_brand_analysis)
                if brand_data:
                    dist_key = 'mayDistribution' if st.session_state.selected_period == 'may' else 'w1Distribution'
                    sku_distribution = brand_data[dist_key]

                    if sku_distribution:
                        df_sku_dist = pd.DataFrame.from_dict(sku_distribution, orient='index')
                        df_sku_dist.reset_index(inplace=True)
                        df_sku_dist.rename(columns={'index': 'SKU', 'itemName': 'Product Name', 'tonnage': 'Tonnage'}, inplace=True)
                        df_sku_dist = df_sku_dist.sort_values(by='Tonnage', ascending=False)

                        display_df_sku = df_sku_dist if st.session_state.show_all_skus else df_sku_dist.head(10)
                        if not display_df_sku.empty:
                            fig_sku_bar = px.bar(display_df_sku, y='SKU', x='Tonnage', orientation='h',
                                                 title=f"SKU Distribution for {st.session_state.selected_brand_analysis} ({period_options[st.session_state.selected_period]})",
                                                 labels={'Tonnage':'Tonnage (Tons)'},
                                                 hover_data=['Product Name'])
                            fig_sku_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                            st.plotly_chart(fig_sku_bar, use_container_width=True)

                            top_n_pie = 5
                            df_pie_data = df_sku_dist.head(top_n_pie).copy()
                            if len(df_sku_dist) > top_n_pie:
                                others_tonnage = df_sku_dist.iloc[top_n_pie:]['Tonnage'].sum()
                                if others_tonnage > 0.01 :
                                    df_pie_data.loc[len(df_pie_data)] = ['Others', 'Other SKUs', others_tonnage, 0]

                            if not df_pie_data.empty:
                                fig_sku_pie = px.pie(df_pie_data, values='Tonnage', names='SKU', 
                                                     title=f"Top SKUs for {st.session_state.selected_brand_analysis} ({period_options[st.session_state.selected_period]})",
                                                     hover_data=['Product Name'])
                                st.plotly_chart(fig_sku_pie, use_container_width=True)
                        else:
                            st.info(f"ไม่มีข้อมูล SKU distribution สำหรับแบรนด์ {st.session_state.selected_brand_analysis} ในช่วงเวลานี้")
                    else:
                        st.info(f"ไม่มีข้อมูล SKU distribution สำหรับแบรนด์ {st.session_state.selected_brand_analysis} ในช่วงเวลานี้")
                else:
                    st.warning(f"ไม่พบข้อมูลสำหรับแบรนด์ {st.session_state.selected_brand_analysis}")

with tab3:
    st.header("ผลลัพธ์แผนการผลิต")
    if not st.session_state.predictions:
        st.info("กรุณาอัปโหลดข้อมูลและสร้างการกระจาย SKU ในแท็บ 'Upload Data' ก่อน")
    else:
        period_options = {'may': 'May', 'w1': 'Week 1'}
        st.radio(
            "เลือกช่วงเวลา (Select Period):",
            options=list(period_options.keys()),
            format_func=lambda x: period_options[x],
            horizontal=True,
            key="results_period_selector"
        )
        
        brand_list_results = list(st.session_state.predictions.keys())
        if not brand_list_results:
            st.warning("ไม่มีข้อมูลการคาดการณ์สำหรับแบรนด์ใดๆ")
        else:
            if st.session_state.selected_brand_results not in brand_list_results:
                 st.session_state.selected_brand_results = brand_list_results[0] if brand_list_results else None

            st.session_state.selected_brand_results = st.selectbox(
                "เลือกแบรนด์ (Select Brand):", 
                options=brand_list_results,
                index=brand_list_results.index(st.session_state.selected_brand_results) if st.session_state.selected_brand_results in brand_list_results else 0,
                key="results_brand_selector"
            )

            if st.session_state.selected_brand_results:
                brand_data_res = st.session_state.predictions.get(st.session_state.selected_brand_results)
                if brand_data_res:
                    dist_key_res = 'mayDistribution' if st.session_state.selected_period == 'may' else 'w1Distribution'
                    sku_distribution_res = brand_data_res[dist_key_res]

                    if sku_distribution_res:
                        df_results = pd.DataFrame.from_dict(sku_distribution_res, orient='index')
                        df_results.reset_index(inplace=True)
                        df_results.rename(columns={'index': 'SKU', 'itemName': 'Product Name', 'tonnage': 'Tonnage', 'percentage': 'Percentage'}, inplace=True)
                        df_results['Percentage'] = (df_results['Percentage'] * 100).round(2).astype(str) + '%'
                        df_results['Tonnage'] = df_results['Tonnage'].round(4)
                        df_results = df_results[['SKU', 'Product Name', 'Tonnage', 'Percentage']].sort_values(by='Tonnage', ascending=False)
                        
                        st.dataframe(df_results, use_container_width=True)
                    else:
                        st.info(f"ไม่มีข้อมูลผลลัพธ์สำหรับแบรนด์ {st.session_state.selected_brand_results} ในช่วงเวลานี้")
                else:
                    st.warning(f"ไม่พบข้อมูลสำหรับแบรนด์ {st.session_state.selected_brand_results}")
        
        if st.session_state.predictions:
            excel_bytes = generate_excel_download(st.session_state.predictions, st.session_state.selected_period)
            st.download_button(
                label="ดาวน์โหลดผลลัพธ์เป็น Excel (Download Results as Excel)",
                data=excel_bytes,
                file_name=f"production_plan_{st.session_state.selected_period}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
