# Production Planning Application - Complete Working Version with Simple AI Analysis
import streamlit as st
import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go
import json
import numpy as np

# Try to import openai, handle if not installed
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

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
    """Process uploaded historical data Excel file - Fixed for pyarrow compatibility"""
    try:
        # Try different header positions with explicit dtype
        header_positions = [0, 1, 2]
        df = None
        
        for header_pos in header_positions:
            try:
                # Read with dtype=str to avoid pyarrow issues
                temp_df = pd.read_excel(uploaded_file, header=header_pos, dtype=str)
                cols_found = sum(1 for col in HISTORICAL_REQUIRED_COLS 
                               if any(req_col.upper() in str(temp_col).upper() 
                                     for temp_col in temp_df.columns 
                                     for req_col in [col]))
                
                if cols_found >= 3:
                    df = temp_df
                    st.success(f"✅ Found valid headers at row {header_pos + 1}")
                    break
            except Exception as e:
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
        
        # Clean data with proper type conversion and error handling
        original_count = len(df)
        
        # Convert TON column with better error handling
        df['TON'] = pd.to_numeric(df['TON'].astype(str).str.replace(',', ''), errors='coerce')
        df = df.dropna(subset=['TON'])
        df = df[df['TON'] > 0]
        df = df.dropna(subset=['BRANDPRODUCT', 'Item Code'])
        
        # Ensure string columns are properly converted with null handling
        df['BRANDPRODUCT'] = df['BRANDPRODUCT'].astype(str).str.strip()
        df['Item Code'] = df['Item Code'].astype(str).str.strip()
        df['Item Name'] = df['Item Name'].astype(str).str.strip()
        
        # Remove empty strings and 'nan' strings
        df = df[df['BRANDPRODUCT'] != '']
        df = df[df['BRANDPRODUCT'] != 'nan']
        df = df[df['Item Code'] != '']
        df = df[df['Item Code'] != 'nan']
        
        st.write(f"📊 **Data Summary:** {len(df):,} valid records from {original_count:,} total rows")
        
        # Brand summary with error handling
        try:
            brand_summary = df.groupby('BRANDPRODUCT').agg({
                'Item Code': 'nunique',
                'TON': ['count', 'sum']
            }).round(2)
            brand_summary.columns = ['Unique SKUs', 'Records', 'Total TON']
            brand_summary = brand_summary.sort_values('Total TON', ascending=False)
            
            st.dataframe(brand_summary, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not generate brand summary: {e}")
        
        return df
        
    except Exception as e:
        st.error(f"Error processing historical file: {e}")
        return None

def process_target_file(uploaded_file):
    """Process BNI Sales Rolling target file - Fixed for pyarrow compatibility"""
    try:
        # Read with explicit dtype to avoid pyarrow issues
        df = pd.read_excel(uploaded_file, sheet_name=0, header=None, dtype=str)
        
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
                try:
                    cell_value = str(df.iloc[row_idx, col_idx]).strip().lower()
                    if 'may' in cell_value and may_col_idx is None:
                        may_col_idx = col_idx
                    elif 'w1' in cell_value and w1_col_idx is None:
                        w1_col_idx = col_idx
                except:
                    continue
        
        if may_col_idx is None:
            may_col_idx = 1
        if w1_col_idx is None:
            w1_col_idx = 2
        
        # Find data range
        start_row_idx = 2
        end_row_idx = len(df)
        
        for i in range(start_row_idx, len(df)):
            if i < len(df):
                try:
                    cell_value = str(df.iloc[i, 0]).strip().lower()
                    if 'total' in cell_value:
                        end_row_idx = i
                        break
                except:
                    continue
        
        # Extract categories with better error handling
        category_data = []
        for i in range(start_row_idx, end_row_idx):
            if i < len(df):
                try:
                    category_name = df.iloc[i, 0]
                    may_value = df.iloc[i, may_col_idx] if may_col_idx < len(df.columns) else "0"
                    w1_value = df.iloc[i, w1_col_idx] if w1_col_idx < len(df.columns) else "0"
                    
                    if pd.notna(category_name) and str(category_name).strip() != '' and str(category_name).strip() != 'nan':
                        try:
                            may_value = float(str(may_value).replace(',', '').strip()) if pd.notna(may_value) and str(may_value).strip() != 'nan' else 0
                        except:
                            may_value = 0
                        
                        try:
                            w1_value = float(str(w1_value).replace(',', '').strip()) if pd.notna(w1_value) and str(w1_value).strip() != 'nan' else 0
                        except:
                            w1_value = 0
                        
                        category_data.append({
                            'Category': str(category_name).strip(),
                            'MayTarget': may_value,
                            'W1Target': w1_value
                        })
                except Exception as e:
                    continue
        
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

def filter_historical_by_month(historical_df, target_month="May"):
    """Filter historical data by month for proper comparison"""
    if historical_df is None or historical_df.empty:
        return historical_df
    
    # Look for date columns
    date_columns = []
    for col in historical_df.columns:
        if any(date_word in str(col).lower() for date_word in ['date', 'time', 'month', 'period']):
            date_columns.append(col)
    
    # If we find date columns, try to filter by month
    if date_columns:
        for date_col in date_columns:
            try:
                # Convert to datetime
                historical_df[date_col] = pd.to_datetime(historical_df[date_col], errors='coerce')
                
                # Filter by month name
                month_number = {
                    'january': 1, 'february': 2, 'march': 3, 'april': 4,
                    'may': 5, 'june': 6, 'july': 7, 'august': 8,
                    'september': 9, 'october': 10, 'november': 11, 'december': 12
                }.get(target_month.lower(), 5)  # Default to May
                
                filtered_df = historical_df[historical_df[date_col].dt.month == month_number]
                
                if len(filtered_df) > 0:
                    st.info(f"📅 Filtered historical data to {target_month} only: {len(filtered_df):,} records")
                    return filtered_df
            except:
                continue
    
    # If no date filtering possible, return original data
    st.info("📅 Using all historical data (no date filtering applied)")
    return historical_df

def map_categories_to_brands(category_targets, historical_df):
    """Map categories to brands with optimized processing"""
    historical_summary = {}
    if historical_df is not None and not historical_df.empty:
        try:
            hist_summary = historical_df.groupby('BRANDPRODUCT')['TON'].sum()
            historical_summary = hist_summary.to_dict()
        except Exception as e:
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
        
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)
    
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
    
    if predictions:
        st.success(f"✅ Generated predictions for {len(predictions)} brands")
        
        # Show prediction summary
        summary_data = []
        for brand, pred in predictions.items():
            historical_tonnage = pred.get('historicalTonnage', 0)
            growth_may = pred['mayTarget'] / historical_tonnage if historical_tonnage > 0 else 0
            
            summary_data.append({
                'Brand': brand,
                'SKU Count': pred['skuCount'],
                'May Target': pred['mayTarget'],
                'Historical': historical_tonnage,
                'Growth': f"{growth_may:.1f}x" if historical_tonnage > 0 else "N/A"
            })
        
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)
    
    return predictions, {}

def setup_openai_api():
    """Setup OpenAI API key"""
    if not OPENAI_AVAILABLE:
        return False, "not_installed"
    
    if OPENAI_API_KEY and OPENAI_API_KEY != "sk-YOUR-API-KEY-HERE":
        return True, "environment"
    else:
        api_key = st.session_state.get('openai_api_key')
        if api_key:
            return True, "user_input"
    
    return False, "no_key"

def display_insights_section(brand_targets_agg, predictions, selected_brand):
    """Simple and working AI insights section"""
    
    st.subheader("🤖 AI Strategic Analysis")
    
    try:
        # คำนวณข้อมูลพื้นฐาน
        total_may = sum(targets['mayTarget'] for targets in brand_targets_agg.values())
        total_historical = sum(targets.get('historicalTonnage', 0) for targets in brand_targets_agg.values())
        growth_rate = (total_may / total_historical) if total_historical > 0 else 0
        
        # แสดงผลสรุปทันที
        st.markdown("### 📊 Production Analysis Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total May Target", f"{total_may:.1f} tons")
        with col2:
            st.metric("Historical Total", f"{total_historical:.1f} tons")
        with col3:
            st.metric("Growth Factor", f"{growth_rate:.1f}x")
        with col4:
            brand_count = len(brand_targets_agg)
            st.metric("Brands", brand_count)
        
        # ตารางวิเคราะห์แบรนด์
        st.markdown("### 📋 Brand Analysis Table")
        
        brand_data = []
        high_risk_count = 0
        
        for brand, targets in brand_targets_agg.items():
            historical = targets.get('historicalTonnage', 0)
            may_target = targets['mayTarget']
            brand_growth = may_target / historical if historical > 0 else 0
            
            # ประเมินความเสี่ยง
            if brand_growth > 3:
                risk = "🔴 High"
                high_risk_count += 1
            elif brand_growth > 1.5:
                risk = "🟡 Medium"
            else:
                risk = "🟢 Low"
            
            # คำนวณ SKU count
            sku_count = len(predictions.get(brand, {}).get('mayDistribution', {}))
            
            brand_data.append({
                'Brand': brand,
                'May Target (tons)': f"{may_target:.1f}",
                'Historical (tons)': f"{historical:.1f}",
                'Growth Factor': f"{brand_growth:.1f}x",
                'Risk Level': risk,
                'SKU Count': sku_count
            })
        
        df_brands = pd.DataFrame(brand_data)
        st.dataframe(df_brands, use_container_width=True, height=300)
        
        # กราฟวิเคราะห์
        st.markdown("### 📈 Visual Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # กราฟ May Targets
            brands = list(brand_targets_agg.keys())
            targets = [targets['mayTarget'] for targets in brand_targets_agg.values()]
            
            fig_bar = px.bar(
                x=brands, 
                y=targets,
                title="May Targets by Brand",
                labels={'x': 'Brand', 'y': 'Target (tons)'},
                color=targets,
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col2:
            # กราฟ Risk Distribution
            risk_data = []
            for item in brand_data:
                risk_level = item['Risk Level'].replace('🔴 ', '').replace('🟡 ', '').replace('🟢 ', '')
                risk_data.append(risk_level)
            
            risk_counts = pd.Series(risk_data).value_counts()
            
            fig_pie = px.pie(
                values=risk_counts.values,
                names=risk_counts.index,
                title="Risk Level Distribution",
                color_discrete_map={
                    'High': '#ff4444',
                    'Medium': '#ffaa00',
                    'Low': '#44ff44'
                }
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # AI Insights (Static Analysis)
        st.markdown("### 🧠 AI Production Insights")
        
        # Production Feasibility
        if growth_rate > 3:
            feasibility = "🔴 High Risk"
            feasibility_text = "เป้าหมายการผลิตสูงมาก ต้องการการวางแผนอย่างระมัดระวัง"
        elif growth_rate > 2:
            feasibility = "🟡 Medium Risk"
            feasibility_text = "เป้าหมายการผลิตสูงปานกลาง ควรมีแผนการจัดการความเสี่ยง"
        else:
            feasibility = "🟢 Low Risk"
            feasibility_text = "เป้าหมายการผลิตอยู่ในระดับที่จัดการได้"
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🎯 Production Feasibility Assessment**")
            if "High Risk" in feasibility:
                st.error(f"{feasibility}")
            elif "Medium Risk" in feasibility:
                st.warning(f"{feasibility}")
            else:
                st.success(f"{feasibility}")
            
            st.info(feasibility_text)
            
            st.markdown("**📊 Key Metrics:**")
            st.markdown(f"• Total production increase: **{((growth_rate-1)*100):.1f}%**")
            st.markdown(f"• High-risk brands: **{high_risk_count}** out of {brand_count}")
            st.markdown(f"• Average growth per brand: **{growth_rate:.1f}x**")
        
        with col2:
            st.markdown("**💡 Strategic Recommendations**")
            
            recommendations = []
            if growth_rate > 3:
                recommendations.extend([
                    "🔍 Implement enhanced quality control measures",
                    "📅 Develop phased production schedule",
                    "👥 Consider additional skilled workforce",
                    "⚡ Plan for equipment capacity expansion"
                ])
            elif growth_rate > 2:
                recommendations.extend([
                    "📋 Optimize production scheduling",
                    "🔧 Regular equipment maintenance checks",
                    "📈 Monitor progress weekly",
                    "🎯 Focus on high-volume SKUs first"
                ])
            else:
                recommendations.extend([
                    "✅ Current capacity should be sufficient",
                    "📊 Monitor standard KPIs",
                    "🔄 Maintain existing quality standards",
                    "💰 Optimize for cost efficiency"
                ])
            
            for rec in recommendations:
                st.markdown(f"• {rec}")
        
        # Detailed Brand Recommendations
        if high_risk_count > 0:
            st.markdown("### ⚠️ High-Risk Brand Focus Areas")
            
            for brand, targets in brand_targets_agg.items():
                historical = targets.get('historicalTonnage', 0)
                may_target = targets['mayTarget']
                brand_growth = may_target / historical if historical > 0 else 0
                
                if brand_growth > 3:
                    with st.expander(f"🔴 {brand} - High Risk Analysis"):
                        st.markdown(f"**Growth Factor:** {brand_growth:.1f}x")
                        st.markdown(f"**Target:** {may_target:.1f} tons")
                        st.markdown(f"**Historical:** {historical:.1f} tons")
                        
                        st.markdown("**Specific Recommendations:**")
                        st.markdown("• ⚡ Priority scheduling for this brand")
                        st.markdown("• 🔍 Enhanced quality checkpoints")
                        st.markdown("• 📦 Careful SKU sequencing")
                        st.markdown("• 👥 Assign experienced operators")
                        st.markdown("• 📊 Daily progress monitoring")
        
        # Advanced AI Analysis (Using Environment API Key)
        st.divider()
        st.markdown("### 🚀 Advanced AI Analysis")
        
        # Check for OpenAI and API Key from environment
        if OPENAI_AVAILABLE and OPENAI_API_KEY:
            st.info("🤖 OpenAI API Key detected from environment - Ready for AI analysis")
            
            # Advanced analysis button
            if st.button("🧠 Generate Advanced AI Insights", 
                        type="primary", 
                        use_container_width=True):
                
                with st.spinner("🤖 AI is analyzing your production plan..."):
                    try:
                        # Call OpenAI API using environment key
                        from openai import OpenAI
                        client = OpenAI(api_key=OPENAI_API_KEY)
                        
                        # Advanced AI prompt with comprehensive production analysis
                        brand_details = []
                        total_skus = 0
                        capacity_utilization = 0
                        
                        for brand, targets in brand_targets_agg.items():
                            historical = targets.get('historicalTonnage', 0)
                            may_target = targets['mayTarget']
                            w1_target = targets['w1Target']
                            sku_count = len(predictions.get(brand, {}).get('mayDistribution', {}))
                            total_skus += sku_count
                            
                            growth_ratio = may_target / historical if historical > 0 else 0
                            capacity_req = min((may_target / 1000) * 100, 100)  # Assuming 1000 tons max capacity
                            capacity_utilization += capacity_req
                            
                            setup_complexity = min(2 + (sku_count / 10) + (growth_ratio / 2), 10)
                            
                            brand_details.append({
                                "brand": brand,
                                "may_target": may_target,
                                "historical": historical,
                                "w1_target": w1_target,
                                "growth_ratio": round(growth_ratio, 2),
                                "sku_count": sku_count,
                                "capacity_requirement": round(capacity_req, 1),
                                "setup_complexity": round(setup_complexity, 1),
                                "categories": targets.get('categories', [])
                            })
                        
                        # Calculate advanced metrics
                        avg_setup_complexity = sum(b['setup_complexity'] for b in brand_details) / len(brand_details)
                        high_growth_brands = [b for b in brand_details if b['growth_ratio'] > 3]
                        medium_growth_brands = [b for b in brand_details if 1.5 <= b['growth_ratio'] <= 3]
                        total_labor_hours = total_may * 8  # 8 hours per ton
                        total_machine_hours = total_may * 6  # 6 machine hours per ton
                        estimated_lead_time = 7 * (1 + avg_setup_complexity/10)
                        
                        prompt = f"""
                        As a senior production planning manager with 15+ years experience in PVC manufacturing, analyze this comprehensive production scenario for May 2024. This is a critical month-end push requiring strategic decision-making.

                        PRODUCTION OVERVIEW:
                        - Total May Target: {total_may:.1f} tons ({((growth_rate-1)*100):.1f}% increase from historical)
                        - Total Historical: {total_historical:.1f} tons
                        - Number of Brands: {brand_count}
                        - Total SKUs: {total_skus}
                        - Estimated Total Labor Hours: {total_labor_hours:,.0f} hours
                        - Estimated Total Machine Hours: {total_machine_hours:,.0f} hours
                        - Average Setup Complexity: {avg_setup_complexity:.1f}/10
                        - Estimated Lead Time: {estimated_lead_time:.1f} days
                        - Overall Capacity Utilization: {capacity_utilization:.1f}%

                        DETAILED BRAND ANALYSIS:
                        {json.dumps(brand_details, indent=2)}

                        HIGH RISK SCENARIOS:
                        - Brands with >3x growth: {len(high_growth_brands)} brands
                        - Brands with 1.5-3x growth: {len(medium_growth_brands)} brands
                        - Setup complexity >7: {len([b for b in brand_details if b['setup_complexity'] > 7])} brands

                        CRITICAL ANALYSIS REQUIRED:

                        1. **PRODUCTION FEASIBILITY & BOTTLENECK ANALYSIS**
                           - Detailed capacity assessment vs targets
                           - Identification of critical bottlenecks (machines, labor, materials)
                           - Risk probability assessment for missing targets
                           - Equipment utilization optimization strategies

                        2. **STRATEGIC PRODUCTION SEQUENCING**
                           - Optimal brand production sequence based on complexity and risk
                           - Changeover time minimization strategies
                           - Parallel processing opportunities
                           - Buffer time allocation for high-risk brands

                        3. **RESOURCE OPTIMIZATION & WORKFORCE PLANNING**
                           - Precise labor allocation (operators, supervisors, QC staff)
                           - Skill requirements and training needs
                           - Overtime planning and cost implications
                           - Equipment maintenance scheduling during production

                        4. **QUALITY ASSURANCE & RISK MITIGATION**
                           - Quality control checkpoints for each growth category
                           - First-pass yield predictions
                           - Rework contingency planning
                           - Testing protocol optimization

                        5. **COST OPTIMIZATION & PROFITABILITY**
                           - Material procurement timing and bulk purchase opportunities
                           - Energy cost optimization during peak production
                           - Waste reduction strategies for high-volume runs
                           - Margin impact analysis per brand

                        6. **CONTINGENCY PLANNING & SCENARIO ANALYSIS**
                           - Best-case, worst-case, and most-likely scenarios
                           - Equipment failure contingencies
                           - Supply chain disruption responses
                           - Customer communication strategies for delays

                        Provide response in this JSON structure with quantitative metrics and specific actionable recommendations:

                        {{
                            "executive_summary": {{
                                "feasibility_score": "1-10 scale",
                                "success_probability": "percentage with confidence interval",
                                "critical_path_duration": "days",
                                "key_success_factors": ["factor1", "factor2", "factor3"],
                                "major_risks": ["risk1", "risk2", "risk3"],
                                "overall_assessment": "detailed paragraph"
                            }},
                            "production_strategy": {{
                                "optimal_sequence": [
                                    {{"brand": "brand_name", "priority": 1, "justification": "reason"}},
                                    {{"brand": "brand_name", "priority": 2, "justification": "reason"}}
                                ],
                                "changeover_optimization": ["strategy1", "strategy2"],
                                "parallel_processing": {{
                                    "opportunities": ["opp1", "opp2"],
                                    "estimated_time_savings": "hours/days"
                                }},
                                "buffer_allocation": {{
                                    "high_risk_brands": "percentage of time",
                                    "medium_risk_brands": "percentage of time"
                                }}
                            }},
                            "resource_management": {{
                                "labor_requirements": {{
                                    "operators_needed": "number",
                                    "supervisors_needed": "number",
                                    "qc_staff_needed": "number",
                                    "overtime_hours": "estimated hours",
                                    "skill_gaps": ["gap1", "gap2"]
                                }},
                                "equipment_optimization": {{
                                    "utilization_target": "percentage",
                                    "maintenance_windows": ["window1", "window2"],
                                    "bottleneck_mitigation": ["action1", "action2"]
                                }},
                                "material_strategy": {{
                                    "procurement_timing": "recommendation",
                                    "inventory_levels": "recommendation",
                                    "supplier_coordination": "strategy"
                                }}
                            }},
                            "quality_framework": {{
                                "inspection_points": ["point1", "point2", "point3"],
                                "testing_protocols": {{
                                    "high_risk_products": "protocol description",
                                    "standard_products": "protocol description"
                                }},
                                "yield_predictions": {{
                                    "first_pass_yield": "percentage",
                                    "rework_rate": "percentage"
                                }},
                                "quality_metrics": ["metric1", "metric2", "metric3"]
                            }},
                            "financial_analysis": {{
                                "cost_breakdown": {{
                                    "material_costs": "amount and percentage",
                                    "labor_costs": "amount and percentage",
                                    "overhead_costs": "amount and percentage",
                                    "total_estimated_cost": "amount"
                                }},
                                "profitability_analysis": {{
                                    "margin_per_brand": [
                                        {{"brand": "name", "margin": "percentage"}}
                                    ],
                                    "break_even_point": "tonnage",
                                    "roi_timeline": "months"
                                }},
                                "cost_optimization": ["opportunity1", "opportunity2", "opportunity3"]
                            }},
                            "risk_assessment": {{
                                "operational_risks": [
                                    {{"risk": "description", "probability": "percentage", "impact": "high/medium/low", "mitigation": "strategy"}}
                                ],
                                "supply_chain_risks": [
                                    {{"risk": "description", "probability": "percentage", "mitigation": "strategy"}}
                                ],
                                "market_risks": [
                                    {{"risk": "description", "probability": "percentage", "mitigation": "strategy"}}
                                ],
                                "contingency_plans": ["plan1", "plan2", "plan3"]
                            }},
                            "monitoring_framework": {{
                                "daily_kpis": ["kpi1", "kpi2", "kpi3"],
                                "weekly_reviews": ["metric1", "metric2"],
                                "escalation_triggers": ["trigger1", "trigger2"],
                                "course_correction_protocols": ["protocol1", "protocol2"]
                            }},
                            "implementation_roadmap": {{
                                "week_1": ["milestone1", "milestone2"],
                                "week_2": ["milestone1", "milestone2"],
                                "week_3": ["milestone1", "milestone2"],
                                "week_4": ["milestone1", "milestone2"],
                                "success_metrics": ["metric1", "metric2", "metric3"]
                            }}
                        }}
                        """
                        
                        response = client.chat.completions.create(
                            model="gpt-4o",  # Use stronger model for complex analysis
                            messages=[
                                {"role": "system", "content": "You are a senior production planning manager with 15+ years of experience in PVC manufacturing, specializing in complex multi-brand production optimization. You have deep expertise in capacity planning, resource optimization, quality control, and risk management. Provide detailed, quantitative analysis with specific, actionable recommendations based on real manufacturing constraints and best practices."},
                                {"role": "user", "content": prompt}
                            ],
                            max_tokens=4000,  # Increased for comprehensive response
                            temperature=0.2   # Lower for more precise, analytical response
                        )
                        
                        ai_response = response.choices[0].message.content.strip()
                        
                        # Clean and parse response
                        if ai_response.startswith("```json"):
                            ai_response = ai_response[7:]
                        if ai_response.endswith("```"):
                            ai_response = ai_response[:-3]
                        
                        ai_insights = json.loads(ai_response)
                        
                        # Display comprehensive AI insights with advanced visualization
                        st.success("✅ Advanced AI analysis completed!")
                        
                        # Executive Summary Section
                        exec_summary = ai_insights.get('executive_summary', {})
                        st.markdown("**🎯 AI Executive Assessment**")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            feasibility = exec_summary.get('feasibility_score', 'N/A')
                            st.metric("Feasibility Score", f"{feasibility}/10")
                        with col2:
                            success_prob = exec_summary.get('success_probability', 'N/A')
                            st.metric("Success Probability", success_prob)
                        with col3:
                            critical_path = exec_summary.get('critical_path_duration', 'N/A')
                            st.metric("Critical Path", critical_path)
                        with col4:
                            overall_risk = "🔴 High" if high_risk_count > 2 else "🟡 Medium" if high_risk_count > 0 else "🟢 Low"
                            st.metric("Risk Level", overall_risk)
                        
                        assessment = exec_summary.get('overall_assessment', '')
                        if assessment:
                            st.info(f"**Overall Assessment:** {assessment}")
                        
                        # Success Factors & Major Risks
                        col1, col2 = st.columns(2)
                        with col1:
                            success_factors = exec_summary.get('key_success_factors', [])
                            if success_factors:
                                st.markdown("**✅ Key Success Factors:**")
                                for factor in success_factors:
                                    st.markdown(f"• {factor}")
                        
                        with col2:
                            major_risks = exec_summary.get('major_risks', [])
                            if major_risks:
                                st.markdown("**⚠️ Major Risks:**")
                                for risk in major_risks:
                                    st.markdown(f"• {risk}")
                        
                        # Advanced Analysis Tabs
                        tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 Production Strategy", "👥 Resources", "🔍 Quality & Risk", "💰 Financial", "📊 Implementation"])
                        
                        with tab1:
                            prod_strategy = ai_insights.get('production_strategy', {})
                            
                            # Optimal Sequence
                            st.markdown("**📋 Optimal Production Sequence**")
                            sequence = prod_strategy.get('optimal_sequence', [])
                            if sequence:
                                sequence_df = pd.DataFrame(sequence)
                                st.dataframe(sequence_df, use_container_width=True)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("**⚡ Changeover Optimization**")
                                changeover = prod_strategy.get('changeover_optimization', [])
                                for item in changeover:
                                    st.markdown(f"• {item}")
                            
                            with col2:
                                st.markdown("**🔄 Parallel Processing**")
                                parallel = prod_strategy.get('parallel_processing', {})
                                opportunities = parallel.get('opportunities', [])
                                for opp in opportunities:
                                    st.markdown(f"• {opp}")
                                
                                time_savings = parallel.get('estimated_time_savings', 'N/A')
                                if time_savings != 'N/A':
                                    st.success(f"**Time Savings:** {time_savings}")
                        
                        with tab2:
                            resource_mgmt = ai_insights.get('resource_management', {})
                            
                            # Labor Requirements
                            labor_req = resource_mgmt.get('labor_requirements', {})
                            if labor_req:
                                st.markdown("**👥 Labor Requirements**")
                                
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    operators = labor_req.get('operators_needed', 'N/A')
                                    st.metric("Operators", operators)
                                with col2:
                                    supervisors = labor_req.get('supervisors_needed', 'N/A')
                                    st.metric("Supervisors", supervisors)
                                with col3:
                                    qc_staff = labor_req.get('qc_staff_needed', 'N/A')
                                    st.metric("QC Staff", qc_staff)
                                
                                overtime = labor_req.get('overtime_hours', 'N/A')
                                if overtime != 'N/A':
                                    st.warning(f"**Estimated Overtime:** {overtime}")
                                
                                skill_gaps = labor_req.get('skill_gaps', [])
                                if skill_gaps:
                                    st.markdown("**🎓 Skill Gaps to Address:**")
                                    for gap in skill_gaps:
                                        st.markdown(f"• {gap}")
                            
                            # Equipment Optimization
                            equipment = resource_mgmt.get('equipment_optimization', {})
                            if equipment:
                                st.markdown("**🔧 Equipment Optimization**")
                                utilization = equipment.get('utilization_target', 'N/A')
                                st.info(f"**Target Utilization:** {utilization}")
                                
                                bottlenecks = equipment.get('bottleneck_mitigation', [])
                                if bottlenecks:
                                    st.markdown("**Bottleneck Mitigation:**")
                                    for bottleneck in bottlenecks:
                                        st.markdown(f"• {bottleneck}")
                        
                        with tab3:
                            quality_framework = ai_insights.get('quality_framework', {})
                            risk_assessment = ai_insights.get('risk_assessment', {})
                            
                            # Quality Framework
                            if quality_framework:
                                st.markdown("**🔍 Quality Control Framework**")
                                
                                inspection_points = quality_framework.get('inspection_points', [])
                                if inspection_points:
                                    st.markdown("**Inspection Points:**")
                                    for point in inspection_points:
                                        st.markdown(f"• {point}")
                                
                                yield_pred = quality_framework.get('yield_predictions', {})
                                if yield_pred:
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        first_pass = yield_pred.get('first_pass_yield', 'N/A')
                                        st.metric("First Pass Yield", first_pass)
                                    with col2:
                                        rework_rate = yield_pred.get('rework_rate', 'N/A')
                                        st.metric("Expected Rework", rework_rate)
                            
                            # Risk Assessment
                            if risk_assessment:
                                st.markdown("**⚠️ Risk Assessment Matrix**")
                                
                                operational_risks = risk_assessment.get('operational_risks', [])
                                if operational_risks:
                                    risk_df = pd.DataFrame(operational_risks)
                                    st.dataframe(risk_df, use_container_width=True)
                        
                        with tab4:
                            financial = ai_insights.get('financial_analysis', {})
                            
                            if financial:
                                # Cost Breakdown
                                cost_breakdown = financial.get('cost_breakdown', {})
                                if cost_breakdown:
                                    st.markdown("**💰 Cost Breakdown Analysis**")
                                    
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        material_cost = cost_breakdown.get('material_costs', 'N/A')
                                        st.info(f"**Material:** {material_cost}")
                                    with col2:
                                        labor_cost = cost_breakdown.get('labor_costs', 'N/A')
                                        st.info(f"**Labor:** {labor_cost}")
                                    with col3:
                                        overhead = cost_breakdown.get('overhead_costs', 'N/A')
                                        st.info(f"**Overhead:** {overhead}")
                                    
                                    total_cost = cost_breakdown.get('total_estimated_cost', 'N/A')
                                    if total_cost != 'N/A':
                                        st.success(f"**Total Estimated Cost:** {total_cost}")
                                
                                # Profitability Analysis
                                profitability = financial.get('profitability_analysis', {})
                                if profitability:
                                    st.markdown("**📈 Profitability Analysis**")
                                    
                                    margin_per_brand = profitability.get('margin_per_brand', [])
                                    if margin_per_brand:
                                        margin_df = pd.DataFrame(margin_per_brand)
                                        st.dataframe(margin_df, use_container_width=True)
                                
                                # Cost Optimization
                                cost_opt = financial.get('cost_optimization', [])
                                if cost_opt:
                                    st.markdown("**💡 Cost Optimization Opportunities**")
                                    for opp in cost_opt:
                                        st.markdown(f"• {opp}")
                        
                        with tab5:
                            implementation = ai_insights.get('implementation_roadmap', {})
                            monitoring = ai_insights.get('monitoring_framework', {})
                            
                            # Implementation Roadmap
                            if implementation:
                                st.markdown("**📅 4-Week Implementation Roadmap**")
                                
                                weeks = ['week_1', 'week_2', 'week_3', 'week_4']
                                week_names = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
                                
                                for week, week_name in zip(weeks, week_names):
                                    milestones = implementation.get(week, [])
                                    if milestones:
                                        with st.expander(f"{week_name} Milestones"):
                                            for milestone in milestones:
                                                st.markdown(f"• {milestone}")
                                
                                success_metrics = implementation.get('success_metrics', [])
                                if success_metrics:
                                    st.markdown("**🎯 Success Metrics:**")
                                    for metric in success_metrics:
                                        st.markdown(f"• {metric}")
                            
                            # Monitoring Framework
                            if monitoring:
                                st.markdown("**📊 Monitoring & Control Framework**")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    daily_kpis = monitoring.get('daily_kpis', [])
                                    if daily_kpis:
                                        st.markdown("**Daily KPIs:**")
                                        for kpi in daily_kpis:
                                            st.markdown(f"• {kpi}")
                                
                                with col2:
                                    escalation = monitoring.get('escalation_triggers', [])
                                    if escalation:
                                        st.markdown("**Escalation Triggers:**")
                                        for trigger in escalation:
                                            st.markdown(f"• {trigger}")
                        
                        # Store comprehensive AI insights
                        st.session_state.ai_insights = ai_insights
                        
                    except Exception as e:
                        st.error(f"❌ AI Analysis Error: {str(e)}")
                        st.info("💡 There might be an issue with the API. Please try again.")
        
        elif OPENAI_AVAILABLE and not OPENAI_API_KEY:
            st.warning("⚠️ OpenAI API Key not found in environment variables")
            st.info("💡 Please set OPENAI_API_KEY in your Render environment variables")
        
        else:
            st.info("💡 Install OpenAI library for advanced AI analysis: `pip install openai`")
        
        # Download Analysis
        st.divider()
        st.markdown("### 📥 Download Analysis Results")
        
        # Prepare download data
        analysis_data = {
            'summary': {
                'total_may_target': total_may,
                'total_historical': total_historical,
                'growth_factor': growth_rate,
                'brand_count': brand_count,
                'high_risk_brands': high_risk_count
            },
            'brand_analysis': brand_data,
            'recommendations': recommendations,
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Add AI insights if available
        if st.session_state.get('ai_insights'):
            analysis_data['ai_insights'] = st.session_state.ai_insights
        
        analysis_json = json.dumps(analysis_data, indent=2, ensure_ascii=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📄 Download Complete Analysis (JSON)",
                data=analysis_json,
                file_name=f"production_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col2:
            # Brand analysis CSV
            df_brands_csv = pd.DataFrame(brand_data)
            csv_data = df_brands_csv.to_csv(index=False)
            st.download_button(
                label="📊 Download Brand Analysis (CSV)",
                data=csv_data,
                file_name=f"brand_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
    except Exception as e:
        st.error(f"❌ Error in AI Analysis: {str(e)}")
        st.info("💡 Please ensure you have valid data loaded and try again")

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

def create_period_selector(widget_key):
    """Create period selector widget"""
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
    """Create brand selector widget"""
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

def generate_excel_download(predictions_data, selected_period_key):
    """Generate Excel file for download"""
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
                st.success("✅ Historical data loaded successfully")

    with col2:
        st.subheader("🎯 Target Data")
        target_file = st.file_uploader("Upload Target Excel File", type=['xlsx', 'xls'], key="target")
        
        if target_file:
            st.session_state.category_targets = process_target_file(target_file)
            if st.session_state.category_targets:
                st.success("✅ Target data loaded successfully")

    st.divider()
    
    # Generate button
    generate_disabled = not (st.session_state.historical_df is not None and st.session_state.category_targets is not None)
    
    if st.button("🚀 Generate SKU Distribution", disabled=generate_disabled, type="primary", use_container_width=True):
        with st.spinner("Processing data and generating predictions..."):
            try:
                # Filter historical data by month for proper comparison
                filtered_historical = filter_historical_by_month(st.session_state.historical_df, "May")
                
                # Map categories to brands
                _, st.session_state.brand_targets_agg = map_categories_to_brands(
                    st.session_state.category_targets, filtered_historical)
                
                if st.session_state.brand_targets_agg:
                    # Generate predictions
                    st.session_state.predictions, _ = predict_sku_distribution(
                        st.session_state.brand_targets_agg, filtered_historical)
                    
                    if st.session_state.predictions:
                        st.success("🎉 SKU distribution generated successfully!")
                        st.balloons()
                    else:
                        st.warning("⚠️ No predictions could be generated")
                else:
                    st.error("❌ No brand mappings created")
                    
            except Exception as e:
                st.error(f"❌ Processing error: {str(e)}")

with tab2:
    st.header("📊 Analysis")
    if not st.session_state.predictions:
        st.info("📝 Please upload data and generate SKU distribution first")
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
            show_all_skus = st.checkbox("Show All SKUs", value=False, key="show_all_skus_toggle")

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
                
                display_df_sku = df_sku_dist if show_all_skus else df_sku_dist.head(15)
                
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
        st.info("📝 Please upload data and generate SKU distribution first")
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

st.divider()
st.markdown("🏭 **Production Planning App** | 📊 Precise SKU-level production planning")
