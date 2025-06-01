# Complete AI Analysis - Basic + Advanced with OpenAI API
# แทนที่ functions เหล่านี้ในไฟล์หลัก

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import numpy as np

def calculate_comprehensive_production_metrics(brand_targets_agg, predictions):
    """Calculate comprehensive production metrics with detailed analysis"""
    
    production_metrics = []
    
    try:
        for brand, targets in brand_targets_agg.items():
            try:
                historical = targets.get('historicalTonnage', 0)
                may_target = targets['mayTarget']
                w1_target = targets['w1Target']
                
                # Get SKU data safely
                brand_pred = predictions.get(brand, {})
                may_dist = brand_pred.get('mayDistribution', {})
                sku_count = len(may_dist)
                
                # Calculate detailed metrics
                growth_ratio = may_target / historical if historical > 0 else 5
                capacity_utilization = min((may_target / 1000) * 100, 100) if may_target > 0 else 0
                
                # Setup complexity (1-10 scale)
                setup_complexity = min(2 + (sku_count / 10) + (growth_ratio / 2), 10)
                
                # Resource calculations
                labor_hours = may_target * 8  # 8 hours per ton
                machine_hours = may_target * 6  # 6 machine hours per ton
                operators_needed = max(2, labor_hours / 160)  # 160 hours per month per operator
                
                # Lead time calculation
                base_lead_time = 7
                complexity_factor = setup_complexity / 10
                volume_factor = min(may_target / 500, 2)
                lead_time = base_lead_time * (1 + complexity_factor + volume_factor)
                
                # Quality risk assessment
                if growth_ratio > 3:
                    quality_risk = "High"
                    risk_score = min(8 + (growth_ratio - 3), 10)
                elif growth_ratio > 1.5:
                    quality_risk = "Medium"
                    risk_score = 4 + (growth_ratio - 1.5) * 2
                else:
                    quality_risk = "Low"
                    risk_score = max(1, growth_ratio)
                
                # Cost calculations
                material_cost = may_target * 800  # $800 per ton base
                labor_cost = labor_hours * 25  # $25 per hour
                overhead_cost = may_target * (200 + setup_complexity * 20)  # Variable overhead
                total_cost = material_cost + labor_cost + overhead_cost
                
                # Market share
                total_market = sum(t['mayTarget'] for t in brand_targets_agg.values())
                market_share = (may_target / total_market * 100) if total_market > 0 else 0
                
                production_metrics.append({
                    'brand': brand,
                    'may_target': round(may_target, 1),
                    'historical': round(historical, 1),
                    'w1_target': round(w1_target, 1),
                    'sku_count': sku_count,
                    'growth_ratio': round(growth_ratio, 2),
                    'capacity_utilization': round(capacity_utilization, 1),
                    'setup_complexity': round(setup_complexity, 1),
                    'quality_risk': quality_risk,
                    'risk_score': round(risk_score, 1),
                    'labor_hours': round(labor_hours, 0),
                    'machine_hours': round(machine_hours, 0),
                    'operators_needed': round(operators_needed, 1),
                    'lead_time_days': round(lead_time, 1),
                    'material_cost': round(material_cost, 0),
                    'labor_cost': round(labor_cost, 0),
                    'overhead_cost': round(overhead_cost, 0),
                    'total_cost': round(total_cost, 0),
                    'cost_per_ton': round(total_cost / may_target if may_target > 0 else 0, 0),
                    'market_share': round(market_share, 1)
                })
                
            except Exception as e:
                st.warning(f"Error processing brand {brand}: {e}")
                continue
                
    except Exception as e:
        st.error(f"Error in metrics calculation: {e}")
        return []
    
    return production_metrics

def generate_ai_enhanced_analysis(production_metrics, brand_targets_agg):
    """Generate AI-enhanced analysis using OpenAI API"""
    
    has_api_key, source = setup_openai_api()
    if not has_api_key:
        return None, "No API key available"
    
    try:
        # Get API key
        api_key = OPENAI_API_KEY if OPENAI_API_KEY else st.session_state.get('openai_api_key')
        
        if not api_key:
            return None, "API Key not found"
        
        # Prepare comprehensive data for AI
        total_target = sum(m['may_target'] for m in production_metrics)
        total_cost = sum(m['total_cost'] for m in production_metrics)
        high_risk_brands = [m for m in production_metrics if m['quality_risk'] == 'High']
        avg_growth = np.mean([m['growth_ratio'] for m in production_metrics])
        avg_complexity = np.mean([m['setup_complexity'] for m in production_metrics])
        
        # Enhanced AI prompt for detailed production analysis
        prompt = f"""
        Analyze this comprehensive production planning data and provide detailed strategic insights.
        
        PRODUCTION OVERVIEW:
        - Total Production Target: {total_target:.1f} tons
        - Number of Brands: {len(production_metrics)}
        - Average Growth Rate: {avg_growth:.1f}x
        - High Risk Brands: {len(high_risk_brands)}
        - Total Estimated Cost: ${total_cost:,.0f}
        - Average Setup Complexity: {avg_complexity:.1f}/10
        
        DETAILED BRAND METRICS:
        {json.dumps(production_metrics[:5], indent=2)}
        
        Provide analysis in this JSON structure:
        {{
            "executive_summary": {{
                "production_feasibility": "High/Medium/Low",
                "overall_assessment": "detailed assessment",
                "key_success_factors": ["factor1", "factor2", "factor3"],
                "critical_challenges": ["challenge1", "challenge2", "challenge3"],
                "confidence_level": "High/Medium/Low"
            }},
            "capacity_planning": {{
                "utilization_analysis": "detailed analysis",
                "bottleneck_identification": ["bottleneck1", "bottleneck2"],
                "capacity_recommendations": ["rec1", "rec2", "rec3"],
                "scalability_assessment": "assessment"
            }},
            "resource_optimization": {{
                "labor_strategy": {{
                    "total_operators_needed": "number",
                    "skill_requirements": ["skill1", "skill2"],
                    "training_recommendations": ["training1", "training2"]
                }},
                "equipment_strategy": {{
                    "machine_utilization": "percentage",
                    "equipment_needs": ["need1", "need2"],
                    "maintenance_priorities": ["priority1", "priority2"]
                }},
                "material_planning": {{
                    "procurement_strategy": "strategy",
                    "inventory_recommendations": ["rec1", "rec2"],
                    "supplier_management": "approach"
                }}
            }},
            "production_scheduling": {{
                "optimal_sequence": ["brand1", "brand2", "brand3"],
                "parallel_opportunities": ["opportunity1", "opportunity2"],
                "milestone_planning": {{
                    "week1_targets": "targets",
                    "week2_targets": "targets",
                    "week3_targets": "targets",
                    "week4_targets": "targets"
                }},
                "contingency_planning": ["plan1", "plan2"]
            }},
            "quality_management": {{
                "quality_strategy": "comprehensive strategy",
                "high_risk_focus_areas": ["area1", "area2"],
                "testing_protocols": ["protocol1", "protocol2"],
                "quality_metrics": ["metric1", "metric2", "metric3"]
            }},
            "cost_optimization": {{
                "cost_breakdown_analysis": {{
                    "material_cost_percentage": "percentage",
                    "labor_cost_percentage": "percentage",
                    "overhead_percentage": "percentage"
                }},
                "cost_reduction_opportunities": ["opp1", "opp2", "opp3"],
                "roi_projections": {{
                    "expected_margin": "percentage",
                    "break_even_analysis": "analysis",
                    "profitability_timeline": "timeline"
                }},
                "budget_variance_management": ["strategy1", "strategy2"]
            }},
            "risk_assessment": {{
                "operational_risks": {{
                    "high_probability": ["risk1", "risk2"],
                    "high_impact": ["risk1", "risk2"],
                    "critical_risks": ["risk1", "risk2"]
                }},
                "mitigation_strategies": {{
                    "preventive_measures": ["measure1", "measure2"],
                    "contingency_plans": ["plan1", "plan2"],
                    "monitoring_systems": ["system1", "system2"]
                }},
                "kpi_monitoring": ["kpi1", "kpi2", "kpi3", "kpi4"]
            }},
            "strategic_recommendations": {{
                "immediate_actions": ["action1", "action2", "action3"],
                "short_term_goals": ["goal1", "goal2"],
                "long_term_strategy": "comprehensive strategy",
                "success_metrics": ["metric1", "metric2", "metric3"]
            }}
        }}
        """
        
        # Call OpenAI API
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a senior production planning expert with deep knowledge of manufacturing operations, cost optimization, and strategic planning. Provide comprehensive, actionable insights. Return only valid JSON without markdown formatting."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000,
                temperature=0.3
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Clean response
            if ai_response.startswith("```json"):
                ai_response = ai_response[7:]
            if ai_response.endswith("```"):
                ai_response = ai_response[:-3]
            
            ai_analysis = json.loads(ai_response)
            return ai_analysis, None
            
        except json.JSONDecodeError as e:
            return None, f"JSON parsing error: {str(e)}"
        except Exception as api_error:
            return None, f"API Error: {str(api_error)}"
        
    except Exception as e:
        return None, f"Analysis Error: {str(e)}"

def create_basic_analysis_fallback(production_metrics):
    """Create basic analysis when API is not available"""
    
    total_target = sum(m['may_target'] for m in production_metrics)
    total_cost = sum(m['total_cost'] for m in production_metrics)
    high_risk_count = len([m for m in production_metrics if m['quality_risk'] == 'High'])
    avg_growth = np.mean([m['growth_ratio'] for m in production_metrics])
    
    return {
        "executive_summary": {
            "production_feasibility": "Medium" if avg_growth > 2 else "High",
            "overall_assessment": f"Production target of {total_target:.0f} tons across {len(production_metrics)} brands requires careful planning and resource allocation.",
            "key_success_factors": [
                "Effective capacity planning and utilization",
                "Quality control for high-growth products",
                "Efficient resource allocation and scheduling"
            ],
            "critical_challenges": [
                f"Managing {high_risk_count} high-risk brands",
                "Coordinating complex multi-brand production",
                "Maintaining quality standards during scale-up"
            ],
            "confidence_level": "Medium"
        },
        "capacity_planning": {
            "utilization_analysis": f"Average capacity utilization of {np.mean([m['capacity_utilization'] for m in production_metrics]):.1f}% indicates moderate to high production load",
            "bottleneck_identification": ["Machine changeover time between SKUs", "Quality inspection capacity"],
            "capacity_recommendations": ["Optimize setup procedures", "Consider additional production lines", "Implement parallel processing"],
            "scalability_assessment": "Current capacity sufficient with optimization"
        },
        "cost_optimization": {
            "cost_breakdown_analysis": {
                "material_cost_percentage": "65%",
                "labor_cost_percentage": "20%",
                "overhead_percentage": "15%"
            },
            "cost_reduction_opportunities": ["Bulk material purchasing", "Setup time reduction", "Process automation"],
            "roi_projections": {
                "expected_margin": "15-20%",
                "break_even_analysis": "Break-even expected within 6 months",
                "profitability_timeline": "Full profitability by month 8"
            }
        }
    }

def display_comprehensive_production_dashboard(production_metrics, ai_analysis):
    """Display comprehensive production analysis dashboard"""
    
    if not production_metrics:
        st.warning("No production metrics available")
        return
    
    st.divider()
    st.markdown("### 📊 Comprehensive Production Analysis Dashboard")
    
    # Convert to DataFrame
    df_metrics = pd.DataFrame(production_metrics)
    
    # Executive Summary Section
    display_executive_summary_advanced(ai_analysis, df_metrics)
    
    st.divider()
    
    # Production Metrics Table
    display_detailed_metrics_table(df_metrics)
    
    st.divider()
    
    # Advanced Analytics Charts
    display_advanced_analytics_charts(df_metrics)
    
    st.divider()
    
    # Strategic Analysis Sections
    display_strategic_analysis_sections(ai_analysis, df_metrics)

def display_executive_summary_advanced(ai_analysis, df_metrics):
    """Display advanced executive summary with comprehensive metrics"""
    
    st.markdown("#### 🎯 Executive Summary & Key Metrics")
    
    # Key Performance Indicators
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_target = df_metrics['may_target'].sum()
        st.metric("Total Target", f"{total_target:.1f} tons")
    
    with col2:
        total_cost = df_metrics['total_cost'].sum()
        st.metric("Total Cost", f"${total_cost:,.0f}")
    
    with col3:
        avg_growth = df_metrics['growth_ratio'].mean()
        st.metric("Avg Growth", f"{avg_growth:.1f}x")
    
    with col4:
        high_risk_count = len(df_metrics[df_metrics['quality_risk'] == 'High'])
        st.metric("High Risk Brands", high_risk_count)
    
    with col5:
        avg_lead_time = df_metrics['lead_time_days'].mean()
        st.metric("Avg Lead Time", f"{avg_lead_time:.1f} days")
    
    # AI Assessment
    if ai_analysis:
        exec_summary = ai_analysis.get('executive_summary', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            feasibility = exec_summary.get('production_feasibility', 'Unknown')
            confidence = exec_summary.get('confidence_level', 'Unknown')
            
            if feasibility == 'High':
                st.success(f"✅ Production Feasibility: {feasibility}")
            elif feasibility == 'Medium':
                st.warning(f"⚠️ Production Feasibility: {feasibility}")
            else:
                st.error(f"❌ Production Feasibility: {feasibility}")
            
            st.info(f"🎯 AI Confidence Level: {confidence}")
        
        with col2:
            assessment = exec_summary.get('overall_assessment', '')
            if assessment:
                st.markdown("**📋 Overall Assessment:**")
                st.write(assessment)
        
        # Success Factors and Challenges
        col1, col2 = st.columns(2)
        
        with col1:
            success_factors = exec_summary.get('key_success_factors', [])
            if success_factors:
                st.markdown("**✅ Key Success Factors:**")
                for factor in success_factors:
                    st.markdown(f"• {factor}")
        
        with col2:
            challenges = exec_summary.get('critical_challenges', [])
            if challenges:
                st.markdown("**⚠️ Critical Challenges:**")
                for challenge in challenges:
                    st.markdown(f"• {challenge}")

def display_detailed_metrics_table(df_metrics):
    """Display detailed production metrics table"""
    
    st.markdown("#### 📋 Detailed Production Metrics")
    
    # Prepare display DataFrame
    display_df = df_metrics[[
        'brand', 'may_target', 'sku_count', 'growth_ratio', 'capacity_utilization',
        'setup_complexity', 'quality_risk', 'lead_time_days', 'cost_per_ton', 'market_share'
    ]].copy()
    
    display_df.columns = [
        'Brand', 'Target (tons)', 'SKU Count', 'Growth Ratio', 'Capacity (%)',
        'Setup Complexity', 'Quality Risk', 'Lead Time (days)', 'Cost/Ton ($)', 'Market Share (%)'
    ]
    
    # Color coding function
    def highlight_metrics(val):
        if isinstance(val, str):
            if val == 'High':
                return 'background-color: #ffebee; color: #c62828'
            elif val == 'Medium':
                return 'background-color: #fff3e0; color: #ef6c00'
            elif val == 'Low':
                return 'background-color: #e8f5e8; color: #2e7d32'
        elif isinstance(val, (int, float)):
            if 'Growth Ratio' in str(val) and val > 3:
                return 'background-color: #ffebee'
            elif 'Capacity' in str(val) and val > 80:
                return 'background-color: #fff3e0'
        return ''
    
    # Apply styling
    styled_df = display_df.style.applymap(highlight_metrics, subset=['Quality Risk'])
    st.dataframe(styled_df, use_container_width=True, height=400)
    
    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_operators = df_metrics['operators_needed'].sum()
        st.metric("Total Operators Needed", f"{total_operators:.0f}")
    
    with col2:
        total_labor_hours = df_metrics['labor_hours'].sum()
        st.metric("Total Labor Hours", f"{total_labor_hours:,.0f}")
    
    with col3:
        avg_complexity = df_metrics['setup_complexity'].mean()
        st.metric("Avg Setup Complexity", f"{avg_complexity:.1f}/10")
    
    with col4:
        total_machine_hours = df_metrics['machine_hours'].sum()
        st.metric("Total Machine Hours", f"{total_machine_hours:,.0f}")

def display_advanced_analytics_charts(df_metrics):
    """Display advanced analytics charts"""
    
    st.markdown("#### 📈 Advanced Production Analytics")
    
    # Create subplots
    col1, col2 = st.columns(2)
    
    with col1:
        # Risk vs Capacity Analysis
        fig_risk_capacity = px.scatter(
            df_metrics,
            x='capacity_utilization',
            y='risk_score',
            size='may_target',
            color='quality_risk',
            hover_name='brand',
            hover_data=['setup_complexity', 'lead_time_days'],
            title="Risk vs Capacity Utilization Analysis",
            labels={
                'capacity_utilization': 'Capacity Utilization (%)',
                'risk_score': 'Risk Score (1-10)',
                'may_target': 'Target (tons)'
            },
            color_discrete_map={
                'High': '#ff4444',
                'Medium': '#ffaa00',
                'Low': '#44ff44'
            }
        )
        fig_risk_capacity.add_hline(y=7, line_dash="dash", line_color="red", annotation_text="High Risk Threshold")
        fig_risk_capacity.add_vline(x=80, line_dash="dash", line_color="orange", annotation_text="High Utilization")
        st.plotly_chart(fig_risk_capacity, use_container_width=True)
    
    with col2:
        # Cost Efficiency Analysis
        fig_cost_efficiency = px.scatter(
            df_metrics,
            x='may_target',
            y='cost_per_ton',
            size='sku_count',
            color='setup_complexity',
            hover_name='brand',
            title="Cost Efficiency vs Volume Analysis",
            labels={
                'may_target': 'Production Target (tons)',
                'cost_per_ton': 'Cost per Ton ($)',
                'sku_count': 'SKU Count',
                'setup_complexity': 'Setup Complexity'
            },
            color_continuous_scale='RdYlGn_r'
        )
        st.plotly_chart(fig_cost_efficiency, use_container_width=True)
    
    # Resource Allocation Chart
    col1, col2 = st.columns(2)
    
    with col1:
        # Labor Resource Allocation
        fig_labor = px.bar(
            df_metrics,
            x='brand',
            y='operators_needed',
            color='quality_risk',
            title="Labor Resource Allocation by Brand",
            labels={'operators_needed': 'Operators Needed'},
            color_discrete_map={
                'High': '#ff4444',
                'Medium': '#ffaa00',
                'Low': '#44ff44'
            }
        )
        st.plotly_chart(fig_labor, use_container_width=True)
    
    with col2:
        # Timeline vs Complexity
        fig_timeline = px.scatter(
            df_metrics,
            x='setup_complexity',
            y='lead_time_days',
            size='may_target',
            color='brand',
            title="Lead Time vs Setup Complexity",
            labels={
                'setup_complexity': 'Setup Complexity (1-10)',
                'lead_time_days': 'Lead Time (days)'
            }
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

def display_strategic_analysis_sections(ai_analysis, df_metrics):
    """Display strategic analysis sections"""
    
    if not ai_analysis:
        return
    
    st.markdown("#### 💡 Strategic Analysis & Recommendations")
    
    # Create tabs for different analysis sections
    tab1, tab2, tab3, tab4 = st.tabs(["🏭 Capacity & Resources", "📅 Production Planning", "🔍 Quality & Risk", "💰 Cost Optimization"])
    
    with tab1:
        display_capacity_resource_analysis(ai_analysis, df_metrics)
    
    with tab2:
        display_production_planning_analysis(ai_analysis)
    
    with tab3:
        display_quality_risk_analysis(ai_analysis, df_metrics)
    
    with tab4:
        display_cost_optimization_analysis(ai_analysis, df_metrics)

def display_capacity_resource_analysis(ai_analysis, df_metrics):
    """Display capacity and resource analysis"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🏭 Capacity Planning**")
        
        capacity_planning = ai_analysis.get('capacity_planning', {})
        
        utilization = capacity_planning.get('utilization_analysis', 'N/A')
        st.info(f"**Analysis:** {utilization}")
        
        bottlenecks = capacity_planning.get('bottleneck_identification', [])
        if bottlenecks:
            st.markdown("**Identified Bottlenecks:**")
            for bottleneck in bottlenecks:
                st.markdown(f"🔴 {bottleneck}")
        
        recommendations = capacity_planning.get('capacity_recommendations', [])
        if recommendations:
            st.markdown("**Capacity Recommendations:**")
            for rec in recommendations:
                st.markdown(f"💡 {rec}")
    
    with col2:
        st.markdown("**👥 Resource Optimization**")
        
        resource_opt = ai_analysis.get('resource_optimization', {})
        
        # Labor Strategy
        labor_strategy = resource_opt.get('labor_strategy', {})
        if labor_strategy:
            total_operators = labor_strategy.get('total_operators_needed', 'N/A')
            st.metric("Recommended Total Operators", total_operators)
            
            skills = labor_strategy.get('skill_requirements', [])
            if skills:
                st.markdown("**Required Skills:**")
                for skill in skills:
                    st.markdown(f"• {skill}")
        
        # Equipment Strategy
        equipment_strategy = resource_opt.get('equipment_strategy', {})
        if equipment_strategy:
            utilization = equipment_strategy.get('machine_utilization', 'N/A')
            st.info(f"**Machine Utilization:** {utilization}")

def display_production_planning_analysis(ai_analysis):
    """Display production planning analysis"""
    
    production_scheduling = ai_analysis.get('production_scheduling', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📅 Production Sequence**")
        
        sequence = production_scheduling.get('optimal_sequence', [])
        if sequence:
            st.markdown("**Recommended Production Order:**")
            for i, brand in enumerate(sequence, 1):
                st.markdown(f"{i}. {brand}")
        
        opportunities = production_scheduling.get('parallel_opportunities', [])
        if opportunities:
            st.markdown("**Parallel Processing Opportunities:**")
            for opp in opportunities:
                st.markdown(f"⚡ {opp}")
    
    with col2:
        st.markdown("**🎯 Milestone Planning**")
        
        milestones = production_scheduling.get('milestone_planning', {})
        if milestones:
            for week, target in milestones.items():
                if target and target != 'targets':
                    st.markdown(f"**{week.replace('_', ' ').title()}:** {target}")
        
        contingency = production_scheduling.get('contingency_planning', [])
        if contingency:
            st.markdown("**Contingency Plans:**")
            for plan in contingency:
                st.markdown(f"🛡️ {plan}")

def display_quality_risk_analysis(ai_analysis, df_metrics):
    """Display quality and risk analysis"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔍 Quality Management**")
        
        quality_mgmt = ai_analysis.get('quality_management', {})
        
        strategy = quality_mgmt.get('quality_strategy', 'N/A')
        st.success(f"**Strategy:** {strategy}")
        
        focus_areas = quality_mgmt.get('high_risk_focus_areas', [])
        if focus_areas:
            st.markdown("**High Risk Focus Areas:**")
            for area in focus_areas:
                st.markdown(f"🎯 {area}")
        
        protocols = quality_mgmt.get('testing_protocols', [])
        if protocols:
            st.markdown("**Testing Protocols:**")
            for protocol in protocols:
                st.markdown(f"🧪 {protocol}")
    
    with col2:
        st.markdown("**⚠️ Risk Assessment**")
        
        risk_assessment = ai_analysis.get('risk_assessment', {})
        
        operational_risks = risk_assessment.get('operational_risks', {})
        if operational_risks:
            high_prob = operational_risks.get('high_probability', [])
            if high_prob:
                st.markdown("**High Probability Risks:**")
                for risk in high_prob:
                    st.markdown(f"⚠️ {risk}")
            
            critical_risks = operational_risks.get('critical_risks', [])
            if critical_risks:
                st.markdown("**Critical Risks:**")
                for risk in critical_risks:
                    st.markdown(f"🔴 {risk}")
        
        # Risk distribution pie chart
        risk_counts = df_metrics['quality_risk'].value_counts()
        fig_risk_pie = px.pie(
            values=risk_counts.values,
            names=risk_counts.index,
            title="Quality Risk Distribution",
            color_discrete_map={
                'High': '#ff4444',
                'Medium': '#ffaa00',
                'Low': '#44ff44'
            }
        )
        st.plotly_chart(fig_risk_pie, use_container_width=True)

def display_cost_optimization_analysis(ai_analysis, df_metrics):
    """Display cost optimization analysis"""
    
    cost_opt = ai_analysis.get('cost_optimization', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**💰 Cost Breakdown**")
        
        cost_breakdown = cost_opt.get('cost_breakdown_analysis', {})
        if cost_breakdown:
            material_pct = cost_breakdown.get('material_cost_percentage', '0%')
            labor_pct = cost_breakdown.get('labor_cost_percentage', '0%')
            overhead_pct = cost_breakdown.get('overhead_percentage', '0%')
            
            # Cost breakdown chart
            breakdown_data = pd.DataFrame({
                'Category': ['Material', 'Labor', 'Overhead'],
                'Percentage': [
                    float(material_pct.replace('%', '')),
                    float(labor_pct.replace('%', '')),
                    float(overhead_pct.replace('%', ''))
                ]
            })
            
            fig_breakdown = px.pie(
                breakdown_data,
                values='Percentage',
                names='Category',
                title="Cost Breakdown Analysis",
                color_discrete_sequence=['#ff9999', '#66b3ff', '#99ff99']
            )
            st.plotly_chart(fig_breakdown, use_container_width=True)
    
    with col2:
        st.markdown("**📈 ROI & Profitability**")
        
        roi_projections = cost_opt.get('roi_projections', {})
        if roi_projections:
            expected_margin = roi_projections.get('expected_margin', 'N/A')
            st.metric("Expected Margin", expected_margin)
            
            break_even = roi_projections.get('break_even_analysis', 'N/A')
            st.info(f"**Break-even:** {break_even}")
            
            timeline = roi_projections.get('profitability_timeline', 'N/A')
            st.success(f"**Timeline:** {timeline}")
        
        opportunities = cost_opt.get('cost_reduction_opportunities', [])
        if opportunities:
            st.markdown("**Cost Reduction Opportunities:**")
            for opp in opportunities:
                st.markdown(f"💡 {opp}")

def display_insights_section(brand_targets_agg, predictions, selected_brand):
    """Main function for displaying comprehensive AI insights"""
    
    st.subheader("🤖 AI Production Planning Analysis")
    
    # Basic Analysis (Always Available)
    st.markdown("#### 📊 Basic Production Analysis")
    st.info("🔍 Generate basic production insights from your data")
    
    if st.button("🚀 Generate Basic Analysis", type="secondary", use_container_width=True):
        with st.spinner("📊 Calculating production metrics..."):
            try:
                # Calculate comprehensive metrics
                production_metrics = calculate_comprehensive_production_metrics(brand_targets_agg, predictions)
                
                if not production_metrics:
                    st.error("❌ Failed to calculate production metrics")
                    return
                
                # Create basic analysis
                basic_analysis = create_basic_analysis_fallback(production_metrics)
                
                # Store in session state
                st.session_state.production_metrics = production_metrics
                st.session_state.basic_analysis = basic_analysis
                
                st.success("✅ Basic analysis completed!")
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    # Advanced AI Analysis (Requires API Key)
    st.divider()
    st.markdown("#### 🤖 Advanced AI Analysis")
    
    # Check OpenAI availability
    if not OPENAI_AVAILABLE:
        st.error("❌ OpenAI library not available for advanced analysis")
        st.code("pip install openai", language="bash")
    else:
        # API Key setup
        has_api_key, source = setup_openai_api()
        
        if not has_api_key:
            st.warning("⚠️ OpenAI API Key required for advanced AI analysis")
            
            with st.expander("🔧 Setup OpenAI API Key", expanded=True):
                st.markdown("**For Enhanced AI Insights:**")
                
                if 'openai_api_key' not in st.session_state:
                    st.session_state.openai_api_key = ""
                
                api_key = st.text_input(
                    "Enter OpenAI API Key:",
                    value=st.session_state.openai_api_key,
                    type="password",
                    help="Get your API key from https://platform.openai.com/api-keys"
                )
                st.session_state.openai_api_key = api_key
                
                if api_key:
                    st.success("✅ API Key configured!")
        
        # Advanced analysis button
        analysis_disabled = not (has_api_key or st.session_state.get('openai_api_key'))
        
        if st.button("🧠 Generate Advanced AI Analysis", 
                    type="primary", 
                    use_container_width=True,
                    disabled=analysis_disabled,
                    help="Requires OpenAI API key for comprehensive AI insights"):
            
            with st.spinner("🤖 AI is analyzing your production planning requirements..."):
                try:
                    # Calculate metrics first
                    production_metrics = calculate_comprehensive_production_metrics(brand_targets_agg, predictions)
                    
                    if not production_metrics:
                        st.error("❌ Failed to calculate production metrics")
                        return
                    
                    # Generate AI analysis
                    ai_analysis, error = generate_ai_enhanced_analysis(production_metrics, brand_targets_agg)
                    
                    if error:
                        st.error(f"❌ AI Analysis Error: {error}")
                        # Fall back to basic analysis
                        ai_analysis = create_basic_analysis_fallback(production_metrics)
                        st.warning("⚠️ Using basic analysis as fallback")
                    
                    # Store comprehensive results
                    st.session_state.production_metrics = production_metrics
                    st.session_state.ai_analysis = ai_analysis
                    
                    st.success("✅ Advanced AI analysis completed!")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    # Display Results
    if st.session_state.get('production_metrics'):
        
        # Choose which analysis to display
        if st.session_state.get('ai_analysis'):
            # Display comprehensive AI analysis
            display_comprehensive_production_dashboard(
                st.session_state.production_metrics,
                st.session_state.ai_analysis
            )
        elif st.session_state.get('basic_analysis'):
            # Display basic analysis
            display_comprehensive_production_dashboard(
                st.session_state.production_metrics,
                st.session_state.basic_analysis
            )
        
        # Download Options
        st.divider()
        st.markdown("#### 📥 Export Analysis Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Production metrics CSV
            df_metrics = pd.DataFrame(st.session_state.production_metrics)
            csv_data = df_metrics.to_csv(index=False)
            st.download_button(
                label="📊 Production Metrics (CSV)",
                data=csv_data,
                file_name=f"production_metrics_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # AI Analysis JSON
            if st.session_state.get('ai_analysis'):
                analysis_json = json.dumps(st.session_state.ai_analysis, indent=2, ensure_ascii=False)
                st.download_button(
                    label="🤖 AI Analysis (JSON)",
                    data=analysis_json,
                    file_name=f"ai_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col3:
            # Complete analysis package
            complete_data = {
                'production_metrics': st.session_state.production_metrics,
                'ai_analysis': st.session_state.get('ai_analysis', st.session_state.get('basic_analysis', {})),
                'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            complete_json = json.dumps(complete_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="📦 Complete Package (JSON)",
                data=complete_json,
                file_name=f"complete_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
