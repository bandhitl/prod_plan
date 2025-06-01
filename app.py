# Enhanced AI Analysis Functions for Production Planning App
# Replace the existing AI analysis functions in your main app with these enhanced versions

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import numpy as np

# Note: These functions enhance the existing AI analysis functionality
# Replace the following functions in your main app:
# - generate_insight_analysis() -> generate_enhanced_insight_analysis()
# - display_insights_section() -> display_enhanced_insights_section()

def generate_enhanced_insight_analysis(brand_targets_agg, predictions, selected_brand=None):
    """Generate enhanced AI insights with structured analysis"""
    
    has_api_key, source = setup_openai_api()
    if not has_api_key:
        return None, None, None, None
    
    try:
        # Get API key
        api_key = OPENAI_API_KEY if OPENAI_API_KEY else st.session_state.get('openai_api_key')
        
        if not api_key:
            return None, None, None, None
        
        # Prepare comprehensive analysis data
        total_may_target = sum(targets['mayTarget'] for targets in brand_targets_agg.values())
        total_historical = sum(targets.get('historicalTonnage', 0) for targets in brand_targets_agg.values())
        
        # Brand performance metrics
        brand_metrics = []
        for brand, targets in brand_targets_agg.items():
            historical = targets.get('historicalTonnage', 0)
            may_target = targets['mayTarget']
            w1_target = targets['w1Target']
            
            brand_metrics.append({
                "brand": brand,
                "may_target": may_target,
                "w1_target": w1_target,
                "historical": historical,
                "growth_rate": (may_target / historical * 100) - 100 if historical > 0 else 0,
                "market_share": (may_target / total_may_target * 100) if total_may_target > 0 else 0,
                "risk_score": calculate_risk_score(may_target, historical, w1_target),
                "sku_count": len(predictions.get(brand, {}).get('mayDistribution', {})),
                "category_count": len(targets.get('categories', []))
            })
        
        # Market analysis data
        market_analysis = {
            "total_capacity_requirement": total_may_target,
            "capacity_growth_vs_historical": ((total_may_target / total_historical) - 1) * 100 if total_historical > 0 else 0,
            "high_risk_brands": len([b for b in brand_metrics if b["risk_score"] >= 7]),
            "medium_risk_brands": len([b for b in brand_metrics if 4 <= b["risk_score"] < 7]),
            "low_risk_brands": len([b for b in brand_metrics if b["risk_score"] < 4]),
            "avg_growth_rate": np.mean([b["growth_rate"] for b in brand_metrics if b["growth_rate"] is not None])
        }
        
        # Enhanced AI prompt for structured analysis
        prompt = f"""
        As a senior production planning analyst, provide a comprehensive strategic analysis in JSON format.
        
        PRODUCTION DATA:
        - Total May Target: {total_may_target:.1f} tons
        - Total Historical: {total_historical:.1f} tons
        - Overall Growth: {market_analysis['capacity_growth_vs_historical']:.1f}%
        - Brand Count: {len(brand_metrics)}
        - Brand Metrics: {json.dumps(brand_metrics, indent=2)}
        
        Return ONLY a valid JSON object with this exact structure:
        {{
            "executive_summary": {{
                "key_insights": ["insight1", "insight2", "insight3"],
                "critical_success_factors": ["factor1", "factor2", "factor3"],
                "overall_assessment": "text",
                "confidence_level": "High/Medium/Low"
            }},
            "market_outlook": {{
                "demand_forecast": "text",
                "market_conditions": "text",
                "competitive_landscape": "text",
                "economic_factors": ["factor1", "factor2", "factor3"]
            }},
            "brand_recommendations": [
                {{
                    "brand": "brand_name",
                    "priority": "High/Medium/Low",
                    "action_items": ["action1", "action2"],
                    "risk_mitigation": "text",
                    "resource_allocation": "text"
                }}
            ],
            "operational_strategy": {{
                "production_optimization": ["strategy1", "strategy2"],
                "supply_chain_actions": ["action1", "action2"],
                "quality_priorities": ["priority1", "priority2"],
                "capacity_planning": "text"
            }},
            "financial_projections": {{
                "revenue_impact": "text",
                "cost_considerations": ["cost1", "cost2"],
                "investment_requirements": "text",
                "roi_expectations": "text"
            }},
            "risk_assessment": {{
                "high_risk_areas": ["risk1", "risk2"],
                "mitigation_strategies": ["strategy1", "strategy2"],
                "contingency_plans": "text",
                "monitoring_kpis": ["kpi1", "kpi2"]
            }}
        }}
        """
        
        # Call OpenAI API
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a senior production planning analyst. Return only valid JSON without any markdown formatting or additional text."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2500,
            temperature=0.3
        )
        
        # Parse AI response
        ai_response = response.choices[0].message.content.strip()
        
        # Clean response - remove markdown if present
        if ai_response.startswith("```json"):
            ai_response = ai_response[7:]
        if ai_response.endswith("```"):
            ai_response = ai_response[:-3]
        
        try:
            ai_analysis = json.loads(ai_response)
        except json.JSONDecodeError:
            ai_analysis = None
        
        return ai_analysis, brand_metrics, market_analysis, None
        
    except Exception as e:
        return None, None, None, str(e)

def calculate_risk_score(may_target, historical, w1_target):
    """Calculate risk score for brand (1-10 scale)"""
    if historical <= 0:
        return 8  # High risk for new products
    
    growth_ratio = may_target / historical
    w1_ratio = w1_target / historical if historical > 0 else 0
    
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
    
    # Consistency risk (May vs W1)
    if abs(growth_ratio - w1_ratio) > 2:
        risk_score += 1
    
    return min(risk_score, 10)

def display_enhanced_insights_section(brand_targets_agg, predictions, selected_brand):
    """Display enhanced AI insights with beautiful visualizations"""
    
    st.subheader("🤖 AI Strategic Analysis Dashboard")
    
    # Check OpenAI availability
    if not OPENAI_AVAILABLE:
        st.error("❌ AI Analysis feature requires OpenAI library")
        st.code("pip install openai", language="bash")
        return
    
    # Check API Key availability
    has_api_key, source = setup_openai_api()
    
    if not has_api_key:
        st.warning("⚠️ AI Analysis requires OpenAI API key configuration")
        
        with st.expander("🔧 API Key Setup", expanded=True):
            st.markdown("**Environment Variable (Recommended):**")
            st.code("OPENAI_API_KEY=your_api_key_here", language="bash")
            
            st.markdown("**Temporary Setup:**")
            
            if 'openai_api_key' not in st.session_state:
                st.session_state.openai_api_key = ""
            
            api_key = st.text_input(
                "Enter OpenAI API Key:",
                value=st.session_state.openai_api_key,
                type="password",
                help="Your API key will only be stored temporarily for this session"
            )
            st.session_state.openai_api_key = api_key
    
    # Analysis generation button
    analyze_button = st.button(
        "🚀 Generate AI Strategic Analysis", 
        type="primary", 
        use_container_width=True,
        help="Generate comprehensive strategic analysis with visualizations"
    )
    
    if analyze_button:
        with st.spinner("🧠 Analyzing production data and generating insights..."):
            ai_analysis, brand_metrics, market_analysis, error = generate_enhanced_insight_analysis(
                brand_targets_agg, predictions, selected_brand
            )
            
            if error:
                st.error(f"❌ Analysis Error: {error}")
                return
            
            if not ai_analysis:
                st.error("❌ Failed to generate structured analysis")
                return
            
            # Store results in session state
            st.session_state.ai_analysis = ai_analysis
            st.session_state.brand_metrics = brand_metrics
            st.session_state.market_analysis = market_analysis
            
            st.success("✅ Strategic analysis completed successfully!")
            st.balloons()
    
    # Display saved analysis if available
    if st.session_state.get('ai_analysis'):
        display_ai_analysis_dashboard()

def display_ai_analysis_dashboard():
    """Display the complete AI analysis dashboard"""
    
    ai_analysis = st.session_state.get('ai_analysis')
    brand_metrics = st.session_state.get('brand_metrics', [])
    market_analysis = st.session_state.get('market_analysis', {})
    
    if not ai_analysis:
        return
    
    st.divider()
    st.markdown("### 📊 Strategic Analysis Dashboard")
    
    # Executive Summary Cards
    display_executive_summary_cards(ai_analysis, market_analysis)
    
    st.divider()
    
    # Brand Performance Analysis
    display_brand_performance_analysis(brand_metrics, ai_analysis)
    
    st.divider()
    
    # Market & Risk Analysis
    display_market_risk_analysis(ai_analysis, brand_metrics, market_analysis)
    
    st.divider()
    
    # Operational Recommendations
    display_operational_recommendations(ai_analysis)
    
    st.divider()
    
    # Download options
    display_analysis_download_options(ai_analysis, brand_metrics)

def display_executive_summary_cards(ai_analysis, market_analysis):
    """Display executive summary with metric cards"""
    
    st.markdown("#### 🎯 Executive Summary")
    
    # Key metrics in cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        confidence = ai_analysis.get('executive_summary', {}).get('confidence_level', 'Unknown')
        confidence_color = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}.get(confidence, "⚪")
        st.metric("Confidence Level", f"{confidence_color} {confidence}")
    
    with col2:
        total_capacity = market_analysis.get('total_capacity_requirement', 0)
        st.metric("Total Capacity", f"{total_capacity:.1f} tons")
    
    with col3:
        growth_rate = market_analysis.get('capacity_growth_vs_historical', 0)
        st.metric("Growth Rate", f"{growth_rate:.1f}%", delta=f"{growth_rate:.1f}%" if growth_rate > 0 else None)
    
    with col4:
        high_risk = market_analysis.get('high_risk_brands', 0)
        st.metric("High Risk Brands", high_risk, delta=f"-{high_risk}" if high_risk > 0 else "0")
    
    # Key insights
    insights = ai_analysis.get('executive_summary', {}).get('key_insights', [])
    if insights:
        st.markdown("**🔍 Key Strategic Insights:**")
        for i, insight in enumerate(insights[:3], 1):
            st.markdown(f"{i}. {insight}")
    
    # Overall assessment
    assessment = ai_analysis.get('executive_summary', {}).get('overall_assessment', '')
    if assessment:
        st.info(f"**📋 Overall Assessment:** {assessment}")

def display_brand_performance_analysis(brand_metrics, ai_analysis):
    """Display brand performance with advanced visualizations"""
    
    st.markdown("#### 🏭 Brand Performance Analysis")
    
    if not brand_metrics:
        st.warning("No brand metrics available")
        return
    
    # Convert to DataFrame
    df_brands = pd.DataFrame(brand_metrics)
    
    # Brand performance dashboard
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
            title="🎯 Brand Risk vs Growth Analysis",
            labels={
                'growth_rate': 'Growth Rate (%)',
                'risk_score': 'Risk Score (1-10)',
                'may_target': 'May Target (tons)',
                'market_share': 'Market Share (%)'
            },
            color_continuous_scale='RdYlGn_r'
        )
        
        # Add risk zones
        fig_scatter.add_hline(y=7, line_dash="dash", line_color="red", annotation_text="High Risk Zone")
        fig_scatter.add_hline(y=4, line_dash="dash", line_color="orange", annotation_text="Medium Risk Zone")
        fig_scatter.add_vline(x=100, line_dash="dash", line_color="blue", annotation_text="2x Growth")
        
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    with col2:
        # Market share pie chart
        fig_pie = px.pie(
            df_brands,
            values='market_share',
            names='brand',
            title="🥧 Market Share Distribution (May Targets)",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    # Brand performance table
    st.markdown("**📋 Brand Performance Summary**")
    
    # Format and color-code the table
    display_df = df_brands.copy()
    display_df['Growth Rate'] = display_df['growth_rate'].apply(lambda x: f"{x:.1f}%")
    display_df['Market Share'] = display_df['market_share'].apply(lambda x: f"{x:.1f}%")
    display_df['May Target'] = display_df['may_target'].apply(lambda x: f"{x:.1f}")
    display_df['Risk Level'] = display_df['risk_score'].apply(
        lambda x: "🔴 High" if x >= 7 else "🟡 Medium" if x >= 4 else "🟢 Low"
    )
    
    table_columns = ['brand', 'May Target', 'Growth Rate', 'Market Share', 'Risk Level', 'sku_count']
    table_df = display_df[table_columns].rename(columns={
        'brand': 'Brand',
        'sku_count': 'SKU Count'
    })
    
    st.dataframe(
        table_df,
        use_container_width=True,
        height=300
    )
    
    # Brand recommendations
    recommendations = ai_analysis.get('brand_recommendations', [])
    if recommendations:
        st.markdown("**💡 AI Brand Recommendations**")
        
        for rec in recommendations[:5]:  # Show top 5 recommendations
            brand = rec.get('brand', 'Unknown')
            priority = rec.get('priority', 'Medium')
            actions = rec.get('action_items', [])
            
            priority_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(priority, "⚪")
            
            with st.expander(f"{priority_emoji} {brand} - {priority} Priority"):
                st.markdown(f"**Risk Mitigation:** {rec.get('risk_mitigation', 'N/A')}")
                st.markdown(f"**Resource Allocation:** {rec.get('resource_allocation', 'N/A')}")
                
                if actions:
                    st.markdown("**Action Items:**")
                    for action in actions:
                        st.markdown(f"• {action}")

def display_market_risk_analysis(ai_analysis, brand_metrics, market_analysis):
    """Display market outlook and risk analysis"""
    
    st.markdown("#### 📈 Market Outlook & Risk Assessment")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🌍 Market Outlook**")
        
        market_outlook = ai_analysis.get('market_outlook', {})
        
        if market_outlook.get('demand_forecast'):
            st.info(f"**Demand Forecast:** {market_outlook['demand_forecast']}")
        
        if market_outlook.get('market_conditions'):
            st.info(f"**Market Conditions:** {market_outlook['market_conditions']}")
        
        economic_factors = market_outlook.get('economic_factors', [])
        if economic_factors:
            st.markdown("**Economic Factors:**")
            for factor in economic_factors:
                st.markdown(f"• {factor}")
    
    with col2:
        st.markdown("**⚠️ Risk Assessment**")
        
        risk_assessment = ai_analysis.get('risk_assessment', {})
        
        high_risk_areas = risk_assessment.get('high_risk_areas', [])
        if high_risk_areas:
            st.error("**High Risk Areas:**")
            for risk in high_risk_areas:
                st.markdown(f"🔴 {risk}")
        
        mitigation_strategies = risk_assessment.get('mitigation_strategies', [])
        if mitigation_strategies:
            st.success("**Mitigation Strategies:**")
            for strategy in mitigation_strategies:
                st.markdown(f"✅ {strategy}")
    
    # Risk distribution chart
    if brand_metrics:
        st.markdown("**📊 Risk Distribution Analysis**")
        
        df_brands = pd.DataFrame(brand_metrics)
        
        # Risk distribution
        risk_categories = []
        for _, row in df_brands.iterrows():
            risk_score = row['risk_score']
            if risk_score >= 7:
                risk_categories.append('High Risk')
            elif risk_score >= 4:
                risk_categories.append('Medium Risk')
            else:
                risk_categories.append('Low Risk')
        
        df_brands['Risk Category'] = risk_categories
        
        # Create risk analysis charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Risk distribution bar chart
            risk_counts = df_brands['Risk Category'].value_counts()
            fig_risk_bar = px.bar(
                x=risk_counts.index,
                y=risk_counts.values,
                title="Risk Category Distribution",
                labels={'x': 'Risk Category', 'y': 'Number of Brands'},
                color=risk_counts.index,
                color_discrete_map={
                    'High Risk': '#ff4444',
                    'Medium Risk': '#ffaa00', 
                    'Low Risk': '#44ff44'
                }
            )
            st.plotly_chart(fig_risk_bar, use_container_width=True)
        
        with col2:
            # Risk vs Volume analysis
            fig_risk_volume = px.box(
                df_brands,
                x='Risk Category',
                y='may_target',
                title="Risk Category vs Production Volume",
                labels={'may_target': 'May Target (tons)'},
                color='Risk Category',
                color_discrete_map={
                    'High Risk': '#ff4444',
                    'Medium Risk': '#ffaa00', 
                    'Low Risk': '#44ff44'
                }
            )
            st.plotly_chart(fig_risk_volume, use_container_width=True)

def display_operational_recommendations(ai_analysis):
    """Display operational strategy and recommendations"""
    
    st.markdown("#### ⚙️ Operational Strategy & Recommendations")
    
    operational = ai_analysis.get('operational_strategy', {})
    financial = ai_analysis.get('financial_projections', {})
    
    # Operational recommendations in tabs
    tab1, tab2, tab3 = st.tabs(["🏭 Production", "🚚 Supply Chain", "💰 Financial"])
    
    with tab1:
        st.markdown("**Production Optimization**")
        prod_optimizations = operational.get('production_optimization', [])
        for opt in prod_optimizations:
            st.markdown(f"• {opt}")
        
        quality_priorities = operational.get('quality_priorities', [])
        if quality_priorities:
            st.markdown("**Quality Priorities**")
            for priority in quality_priorities:
                st.markdown(f"🎯 {priority}")
        
        capacity_planning = operational.get('capacity_planning', '')
        if capacity_planning:
            st.info(f"**Capacity Planning:** {capacity_planning}")
    
    with tab2:
        st.markdown("**Supply Chain Actions**")
        supply_actions = operational.get('supply_chain_actions', [])
        for action in supply_actions:
            st.markdown(f"• {action}")
        
        # Add supply chain risk matrix if available
        if st.session_state.get('brand_metrics'):
            df_brands = pd.DataFrame(st.session_state['brand_metrics'])
            
            # Simple supply chain complexity score
            df_brands['SC_Complexity'] = (df_brands['sku_count'] / 10) + (df_brands['may_target'] / 1000)
            
            fig_sc = px.scatter(
                df_brands,
                x='SC_Complexity',
                y='risk_score',
                size='may_target',
                hover_name='brand',
                title="Supply Chain Complexity vs Risk",
                labels={
                    'SC_Complexity': 'Supply Chain Complexity Score',
                    'risk_score': 'Risk Score'
                }
            )
            st.plotly_chart(fig_sc, use_container_width=True)
    
    with tab3:
        st.markdown("**Financial Projections**")
        
        revenue_impact = financial.get('revenue_impact', '')
        if revenue_impact:
            st.success(f"**Revenue Impact:** {revenue_impact}")
        
        investment_requirements = financial.get('investment_requirements', '')
        if investment_requirements:
            st.warning(f"**Investment Requirements:** {investment_requirements}")
        
        cost_considerations = financial.get('cost_considerations', [])
        if cost_considerations:
            st.markdown("**Cost Considerations:**")
            for cost in cost_considerations:
                st.markdown(f"💰 {cost}")
        
        roi_expectations = financial.get('roi_expectations', '')
        if roi_expectations:
            st.info(f"**ROI Expectations:** {roi_expectations}")

def display_analysis_download_options(ai_analysis, brand_metrics):
    """Display download options for analysis results"""
    
    st.markdown("#### 📥 Export Analysis Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # JSON download
        analysis_json = json.dumps(ai_analysis, indent=2, ensure_ascii=False)
        st.download_button(
            label="📄 Download Analysis (JSON)",
            data=analysis_json,
            file_name=f"ai_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with col2:
        # Brand metrics CSV
        if brand_metrics:
            df_metrics = pd.DataFrame(brand_metrics)
            csv_data = df_metrics.to_csv(index=False)
            st.download_button(
                label="📊 Download Metrics (CSV)",
                data=csv_data,
                file_name=f"brand_metrics_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col3:
        # Full report text
        full_report = generate_text_report(ai_analysis, brand_metrics)
        st.download_button(
            label="📋 Download Report (TXT)",
            data=full_report,
            file_name=f"strategic_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )

def generate_text_report(ai_analysis, brand_metrics):
    """Generate a comprehensive text report"""
    
    report = "STRATEGIC PRODUCTION ANALYSIS REPORT\n"
    report += "=" * 50 + "\n\n"
    
    # Executive Summary
    report += "EXECUTIVE SUMMARY\n"
    report += "-" * 20 + "\n"
    
    exec_summary = ai_analysis.get('executive_summary', {})
    report += f"Confidence Level: {exec_summary.get('confidence_level', 'N/A')}\n"
    report += f"Overall Assessment: {exec_summary.get('overall_assessment', 'N/A')}\n\n"
    
    key_insights = exec_summary.get('key_insights', [])
    if key_insights:
        report += "Key Insights:\n"
        for i, insight in enumerate(key_insights, 1):
            report += f"{i}. {insight}\n"
        report += "\n"
    
    # Brand Performance
    if brand_metrics:
        report += "BRAND PERFORMANCE METRICS\n"
        report += "-" * 30 + "\n"
        
        df_brands = pd.DataFrame(brand_metrics)
        for _, row in df_brands.iterrows():
            report += f"Brand: {row['brand']}\n"
            report += f"  May Target: {row['may_target']:.1f} tons\n"
            report += f"  Growth Rate: {row['growth_rate']:.1f}%\n"
            report += f"  Risk Score: {row['risk_score']}/10\n"
            report += f"  Market Share: {row['market_share']:.1f}%\n\n"
    
    # Recommendations
    recommendations = ai_analysis.get('brand_recommendations', [])
    if recommendations:
        report += "BRAND RECOMMENDATIONS\n"
        report += "-" * 25 + "\n"
        
        for rec in recommendations:
            report += f"Brand: {rec.get('brand', 'N/A')}\n"
            report += f"Priority: {rec.get('priority', 'N/A')}\n"
            report += f"Risk Mitigation: {rec.get('risk_mitigation', 'N/A')}\n"
            
            actions = rec.get('action_items', [])
            if actions:
                report += "Action Items:\n"
                for action in actions:
                    report += f"  - {action}\n"
            report += "\n"
    
    # Risk Assessment
    risk_assessment = ai_analysis.get('risk_assessment', {})
    if risk_assessment:
        report += "RISK ASSESSMENT\n"
        report += "-" * 15 + "\n"
        
        high_risks = risk_assessment.get('high_risk_areas', [])
        if high_risks:
            report += "High Risk Areas:\n"
            for risk in high_risks:
                report += f"  - {risk}\n"
            report += "\n"
        
        mitigations = risk_assessment.get('mitigation_strategies', [])
        if mitigations:
            report += "Mitigation Strategies:\n"
            for strategy in mitigations:
                report += f"  - {strategy}\n"
            report += "\n"
    
    report += f"Report Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    return report

# Update the main display function to use the new enhanced version
def display_insights_section(brand_targets_agg, predictions, selected_brand):
    """Main function to display enhanced AI insights section"""
    display_enhanced_insights_section(brand_targets_agg, predictions, selected_brand)
