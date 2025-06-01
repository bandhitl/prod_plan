# Fixed Enhanced AI Analysis Functions
# แทนที่ functions เหล่านี้ในไฟล์หลักของคุณ

import streamlit as st
import pandas as pd
import plotly.express as px
import json
import numpy as np

from openai_utils import (
    setup_openai_api,
    OPENAI_AVAILABLE,
    OPENAI_API_KEY,
)

def calculate_risk_score(may_target, historical, w1_target):
    """Calculate risk score for brand (1-10 scale) - Fixed version"""
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

def generate_enhanced_insight_analysis(brand_targets_agg, predictions, selected_brand=None):
    """Generate enhanced AI insights - Fixed version"""
    
    has_api_key, source = setup_openai_api()
    if not has_api_key:
        return None, None, None, "No API key available"
    
    try:
        # Get API key
        api_key = OPENAI_API_KEY if OPENAI_API_KEY else st.session_state.get('openai_api_key')
        
        if not api_key:
            return None, None, None, "API Key not found"
        
        # Prepare analysis data - Simplified version
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
                model="gpt-4o-mini",  # Use more stable model
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

def create_fallback_analysis(market_analysis, brand_metrics):
    """Create fallback analysis if AI fails"""
    return {
        "executive_summary": {
            "key_insights": [
                f"Total production target: {market_analysis['total_capacity_requirement']} tons",
                f"Growth rate: {market_analysis['capacity_growth_vs_historical']}%",
                f"High risk brands: {market_analysis['high_risk_brands']}"
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

def display_enhanced_insights_section(brand_targets_agg, predictions, selected_brand):
    """Display enhanced AI insights - Fixed version"""
    
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

def display_analysis_results():
    """Display analysis results - Simplified version"""
    
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

# Update the main function call
def display_insights_section(brand_targets_agg, predictions, selected_brand):
    """Updated main function to use enhanced insights"""
    display_enhanced_insights_section(brand_targets_agg, predictions, selected_brand)


def main():
    """Streamlit entry point"""
    st.set_page_config(page_title="Production Planning Insights", layout="wide")
    st.title("Production Planning Insights")

    # Placeholder demo data
    demo_brand_targets = {
        "BrandA": {"mayTarget": 120.0, "w1Target": 30.0, "historicalTonnage": 100.0},
        "BrandB": {"mayTarget": 80.0, "w1Target": 20.0, "historicalTonnage": 70.0},
    }
    demo_predictions = {}

    display_insights_section(demo_brand_targets, demo_predictions, None)


if __name__ == "__main__":
    main()
