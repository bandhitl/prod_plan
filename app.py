# Production Planning Application - Complete Fixed Version
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
        
        # Clean data with proper type conversion
        original_count = len(df)
        df['TON'] = pd.to_numeric(df['TON'], errors='coerce')
        df = df.dropna(subset=['TON'])
        df = df[df['TON'] > 0]
        df = df.dropna(subset=['BRANDPRODUCT', 'Item Code'])
        
        # Ensure string columns are properly converted
        df['BRANDPRODUCT'] = df['BRANDPRODUCT'].astype(str).str.strip()
        df['Item Code'] = df['Item Code'].astype(str).str.strip()
        df['Item Name'] = df['Item Name'].astype(str).str.strip()
        
        # Remove empty strings
        df = df[df['BRANDPRODUCT'] != '']
        df = df[df['Item Code'] != '']
        
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

def calculate_risk_score(may_target, historical, w1_target):
    """Calculate risk score for brand (1-10 scale)"""
    try:
        if historical <= 0:
            return 8  # High risk for new products
        
        growth_ratio = may_target / historical
        
        risk_score = 1
        
        # Growth-based risk
        if growth_ratio > 5:
            risk_score += 4
        elif growth_ratio > 3:
            risk_score += 3
        elif growth_ratio > 2:
            risk_score += 2
        elif growth_ratio > 1.5:
            risk_score += 1
        
        # Volume-based risk
        if may_target > 1000:
            risk_score += 2
        elif may_target > 500:
            risk_score += 1
        
        return min(risk_score, 10)
    except:
        return 5  # Default medium risk

def create_fallback_analysis(market_analysis, brand_metrics):
    """Create fallback analysis if AI fails"""
    return {
        "executive_summary": {
            "key_insights": [
                f"Total production target: {market_analysis.get('total_capacity_requirement', 0)} tons",
                f"Growth rate: {market_analysis.get('capacity_growth_vs_historical', 0)}%",
                f"High risk brands: {market_analysis.get('high_risk_brands', 0)}"
            ],
            "overall_assessment": "Analysis completed with production planning recommendations",
            "confidence_level": "Medium"
        },
        "market_outlook": {
            "demand_forecast": "Market demand shows growth potential",
            "market_conditions": "Current market conditions require careful capacity planning"
        },
        "operational_strategy": {
            "production_optimization": [
                "Focus on high-volume SKUs",
                "Optimize production scheduling"
            ],
            "capacity_planning": "Scale capacity based on growth projections"
        },
        "risk_assessment": {
            "high_risk_areas": [
                "High growth rate targets",
                "New product launches"
            ],
            "mitigation_strategies": [
                "Gradual capacity scaling",
                "Quality control enhancement"
            ]
        }
    }

def generate_enhanced_insight_analysis(brand_targets_agg, predictions, selected_brand=None):
    """Generate enhanced AI insights with structured analysis"""
    
    has_api_key, source = setup_openai_api()
    if not has_api_key:
        return None, None, None, "No API key available"
    
    try:
        # Get API key
        api_key = OPENAI_API_KEY if OPENAI_API_KEY else st.session_state.get('openai_api_key')
        
        if not api_key:
            return None, None, None, "API Key not found"
        
        # Prepare analysis data
        total_may_target = sum(targets['mayTarget'] for targets in brand_targets_agg.values())
        total_historical = sum(targets.get('historicalTonnage', 0) for targets in brand_targets_agg.values())
        
        # Brand metrics with error handling
        brand_metrics = []
        for brand, targets in brand_targets_agg.items():
            try:
                historical = targets.get('historicalTonnage', 0)
                may_target = targets['mayTarget']
                w1_target = targets['w1Target']
                
                growth_rate = ((may_target / historical) - 1) * 100 if historical > 0 else 0
                market_share = (may_target / total_may_target * 100) if total_may_target > 0 else 0
                risk_score = calculate_risk_score(may_target, historical, w1_target)
                sku_count = len(predictions.get(brand, {}).get('mayDistribution', {}))
                
                brand_metrics.append({
                    "brand": brand,
                    "may_target": round(may_target, 2),
                    "w1_target": round(w1_target, 2),
                    "historical": round(historical, 2),
                    "growth_rate": round(growth_rate, 1),
                    "market_share": round(market_share, 1),
                    "risk_score": risk_score,
                    "sku_count": sku_count,
                    "category_count": len(targets.get('categories', []))
                })
            except Exception as e:
                st.warning(f"Error processing brand {brand}: {e}")
                continue
        
        # Market analysis
        market_analysis = {
            "total_capacity_requirement": round(total_may_target, 2),
            "total_historical": round(total_historical, 2),
            "capacity_growth_vs_historical": round(((total_may_target / total_historical) - 1) * 100, 1) if total_historical > 0 else 0,
            "high_risk_brands": len([b for b in brand_metrics if b["risk_score"] >= 7]),
            "medium_risk_brands": len([b for b in brand_metrics if 4 <= b["risk_score"] < 7]),
            "low_risk_brands": len([b for b in brand_metrics if b["risk_score"] < 4]),
            "avg_growth_rate": round(np.mean([b["growth_rate"] for b in brand_metrics]) if brand_metrics else 0, 1),
            "brand_count": len(brand_metrics)
        }
        
        # Simplified AI prompt
        prompt = f"""
        Analyze this production planning data and return ONLY a JSON object:
        
        Total May Target: {total_may_target:.1f} tons
        Total Historical: {total_historical:.1f} tons
        Growth Rate: {market_analysis['capacity_growth_vs_historical']:.1f}%
        Brand Count: {len(brand_metrics)}
        High Risk Brands: {market_analysis['high_risk_brands']}
        
        Return JSON with this structure:
        {{
            "executive_summary": {{
                "key_insights": ["insight1", "insight2", "insight3"],
                "overall_assessment": "brief assessment text",
                "confidence_level": "High"
            }},
            "market_outlook": {{
                "demand_forecast": "brief forecast",
                "market_conditions": "current conditions"
            }},
            "operational_strategy": {{
                "production_optimization": ["strategy1", "strategy2"],
                "capacity_planning": "planning recommendation"
            }},
            "risk_assessment": {{
                "high_risk_areas": ["risk1", "risk2"],
                "mitigation_strategies": ["strategy1", "strategy2"]
            }}
        }}
        """
        
        # Call OpenAI API with error handling
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a production analyst. Return only valid JSON without markdown."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.2
            )
            
            # Parse AI response
            ai_response = response.choices[0].message.content.strip()
            
            # Clean response
            if ai_response.startswith("```json"):
                ai_response = ai_response[7:]
            if ai_response.endswith("```"):
                ai_response = ai_response[:-3]
            
            ai_analysis = json.loads(ai_response)
            
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            ai_analysis = create_fallback_analysis(market_analysis, brand_metrics)
        except Exception as api_error:
            return None, brand_metrics, market_analysis, f"API Error: {str(api_error)}"
        
        return ai_analysis, brand_metrics, market_analysis, None
        
    except Exception as e:
        return None, None, None, f"Analysis Error: {str(e)}"

def display_executive_summary(ai_analysis, market_analysis):
    """Display executive summary with metrics"""
    
    st.markdown("#### 🎯 Executive Summary")
    
    # Metrics cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        confidence = ai_analysis.get('executive_summary', {}).get('confidence_level', 'Medium')
        confidence_color = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}.get(confidence, "⚪")
        st.metric("Confidence", f"{confidence_color} {confidence}")
    
    with col2:
        total_capacity = market_analysis.get('total_capacity_requirement', 0)
        st.metric("Target Capacity", f"{total_capacity:.1f} tons")
    
    with col3:
        growth_rate = market_analysis.get('capacity_growth_vs_historical', 0)
        st.metric("Growth Rate", f"{growth_rate:.1f}%")
    
    with col4:
        high_risk = market_analysis.get('high_risk_brands', 0)
        st.metric("High Risk Brands", high_risk)
    
    # Key insights
    insights = ai_analysis.get('executive_summary', {}).get('key_insights', [])
    if insights:
        st.markdown("**🔍 Key Insights:**")
        for i, insight in enumerate(insights, 1):
            st.markdown(f"{i}. {insight}")
    
    # Overall assessment
    assessment = ai_analysis.get('executive_summary', {}).get('overall_assessment', '')
    if assessment:
        st.info(f"**📋 Assessment:** {assessment}")

def display_brand_performance(brand_metrics):
    """Display brand performance analysis"""
    
    st.markdown("#### 🏭 Brand Performance")
    
    # Convert to DataFrame
    df_brands = pd.DataFrame(brand_metrics)
    
    if df_brands.empty:
        st.warning("No brand data available")
        return
    
    # Performance charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Growth vs Risk scatter plot
        fig_scatter = px.scatter(
            df_brands,
            x='growth_rate',
            y='risk_score',
            size='may_target',
            color='market_share',
            hover_name='brand',
            title="Growth vs Risk Analysis",
            labels={
                'growth_rate': 'Growth Rate (%)',
                'risk_score': 'Risk Score (1-10)',
                'may_target': 'Target (tons)',
                'market_share': 'Market Share (%)'
            }
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    with col2:
        # Market share pie chart
        fig_pie = px.pie(
            df_brands,
            values='market_share',
            names='brand',
            title="Market Share Distribution"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # Performance table
    st.markdown("**📋 Brand Summary**")
    
    display_df = df_brands.copy()
    display_df['Risk Level'] = display_df['risk_score'].apply(
        lambda x: "🔴 High" if x >= 7 else "🟡 Medium" if x >= 4 else "🟢 Low"
    )
    
    table_columns = ['brand', 'may_target', 'growth_rate', 'market_share', 'Risk Level', 'sku_count']
    table_df = display_df[table_columns].rename(columns={
        'brand': 'Brand',
        'may_target': 'Target (tons)',
        'growth_rate': 'Growth (%)',
        'market_share': 'Market Share (%)',
        'sku_count': 'SKUs'
    })
    
    st.dataframe(table_df, use_container_width=True)

def display_recommendations(ai_analysis):
    """Display AI recommendations"""
    
    st.markdown("#### 💡 Strategic Recommendations")
    
    # Market outlook
    market_outlook = ai_analysis.get('market_outlook', {})
    if market_outlook:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🌍 Market Outlook**")
            demand = market_outlook.get('demand_forecast', 'N/A')
            st.info(f"**Demand:** {demand}")
            
            conditions = market_outlook.get('market_conditions', 'N/A')
            st.info(f"**Conditions:** {conditions}")
        
        with col2:
            st.markdown("**⚠️ Risk Assessment**")
            
            risks = ai_analysis.get('risk_assessment', {}).get('high_risk_areas', [])
            if risks:
                for risk in risks[:3]:
                    st.warning(f"🔴 {risk}")
    
    # Operational strategy
    operational = ai_analysis.get('operational_strategy', {})
    if operational:
        st.markdown("**⚙️ Operational Strategy**")
        
        optimizations = operational.get('production_optimization', [])
        if optimizations:
            st.markdown("**Production Optimization:**")
            for opt in optimizations:
                st.markdown(f"• {opt}")
        
        capacity = operational.get('capacity_planning', '')
        if capacity:
            st.success(f"**Capacity Planning:** {capacity}")

def display_analysis_results():
    """Display analysis results"""
    
    ai_analysis = st.session_state.get('ai_analysis')
    brand_metrics = st.session_state.get('brand_metrics', [])
    market_analysis = st.session_state.get('market_analysis', {})
    
    if not ai_analysis:
        return
    
    st.divider()
    st.markdown("### 📊 Analysis Results")
    
    # Executive Summary
    display_executive_summary(ai_analysis, market_analysis)
    
    # Brand Performance
    if brand_metrics:
        display_brand_performance(brand_metrics)
    
    # Recommendations
    display_recommendations(ai_analysis)
    
    # Download section
    st.divider()
    st.markdown("#### 📥 Export Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Download AI analysis as JSON
        analysis_json = json.dumps(ai_analysis, indent=2, ensure_ascii=False)
        st.download_button(
            label="📄 Download Analysis (JSON)",
            data=analysis_json,
            file_name=f"ai_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with col2:
        # Download brand metrics as CSV
        if st.session_state.get('brand_metrics'):
            df_metrics = pd.DataFrame(st.session_state['brand_metrics'])
            csv_data = df_metrics.to_csv(index=False)
            st.download_button(
                label="📊 Download Metrics (CSV)",
                data=csv_data,
                file_name=f"brand_metrics_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

def display_insights_section(brand_targets_agg, predictions, selected_brand):
    """Display enhanced AI insights section"""
    
    st.subheader("🤖 AI Strategic Analysis")
    
    # Check OpenAI availability
    if not OPENAI_AVAILABLE:
        st.error("❌ OpenAI library not available")
        st.code("pip install openai", language="bash")
        return
    
    # API Key setup
    has_api_key, source = setup_openai_api()
    
    if not has_api_key:
        st.warning("⚠️ OpenAI API Key required")
        
        with st.expander("🔧 Setup API Key"):
            if 'openai_api_key' not in st.session_state:
                st.session_state.openai_api_key = ""
            
            api_key = st.text_input(
                "OpenAI API Key:",
                value=st.session_state.openai_api_key,
                type="password"
            )
            st.session_state.openai_api_key = api_key
    
    # Analysis button
    if st.button("🚀 Generate Analysis", type="primary", use_container_width=True):
        with st.spinner("🧠 Analyzing data..."):
            try:
                ai_analysis, brand_metrics, market_analysis, error = generate_enhanced_insight_analysis(
                    brand_targets_agg, predictions, selected_brand
                )
                
                if error:
                    st.error(f"❌ {error}")
                    return
                
                if not ai_analysis:
                    st.error("❌ Failed to generate analysis")
                    return
                
                # Store in session state
                st.session_state.ai_analysis = ai_analysis
                st.session_state.brand_metrics = brand_metrics
                st.session_state.market_analysis = market_analysis
                
                st.success("✅ Analysis completed!")
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    # Display results
    if st.session_state.get('ai_analysis'):
        display_analysis_results()

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
