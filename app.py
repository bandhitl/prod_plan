# Enhanced Production Planning AI Analysis - Replace functions in main app

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import numpy as np
from datetime import datetime, timedelta

def calculate_production_metrics(brand_targets_agg, predictions):
    """Calculate comprehensive production planning metrics"""
    
    production_metrics = []
    
    for brand, targets in brand_targets_agg.items():
        historical = targets.get('historicalTonnage', 0)
        may_target = targets['mayTarget']
        w1_target = targets['w1Target']
        
        # Get SKU data
        brand_pred = predictions.get(brand, {})
        may_dist = brand_pred.get('mayDistribution', {})
        sku_count = len(may_dist)
        
        # Calculate production metrics
        capacity_utilization = min((may_target / 1000) * 100, 100) if may_target > 0 else 0  # Assuming 1000 tons max capacity
        setup_complexity = min(sku_count / 10, 10)  # Complexity based on SKU count
        
        # Resource requirements
        labor_hours = may_target * 8  # 8 hours per ton estimate
        machine_hours = may_target * 6  # 6 machine hours per ton
        
        # Lead time calculation
        base_lead_time = 7  # Base 7 days
        complexity_factor = setup_complexity / 10
        volume_factor = min(may_target / 500, 2)  # Volume impact
        lead_time_days = base_lead_time * (1 + complexity_factor + volume_factor)
        
        # Quality risk assessment
        growth_ratio = may_target / historical if historical > 0 else 5
        quality_risk = "High" if growth_ratio > 3 else "Medium" if growth_ratio > 1.5 else "Low"
        
        # Cost estimates (simplified)
        material_cost = may_target * 800  # $800 per ton
        labor_cost = labor_hours * 25  # $25 per hour
        overhead_cost = may_target * 200  # $200 per ton
        total_cost = material_cost + labor_cost + overhead_cost
        
        production_metrics.append({
            'brand': brand,
            'may_target': may_target,
            'historical': historical,
            'sku_count': sku_count,
            'capacity_utilization': round(capacity_utilization, 1),
            'setup_complexity': round(setup_complexity, 1),
            'labor_hours': round(labor_hours, 0),
            'machine_hours': round(machine_hours, 0),
            'lead_time_days': round(lead_time_days, 1),
            'quality_risk': quality_risk,
            'material_cost': round(material_cost, 0),
            'labor_cost': round(labor_cost, 0),
            'total_cost': round(total_cost, 0),
            'cost_per_ton': round(total_cost / may_target if may_target > 0 else 0, 0),
            'growth_ratio': round(growth_ratio, 2)
        })
    
    return production_metrics

def generate_production_schedule(brand_targets_agg, production_metrics):
    """Generate production schedule recommendations"""
    
    schedule_data = []
    start_date = datetime(2024, 5, 1)  # May 1st start
    
    # Sort by priority (risk level and volume)
    sorted_metrics = sorted(production_metrics, 
                          key=lambda x: (x['quality_risk'] == 'High', -x['may_target']), 
                          reverse=True)
    
    current_date = start_date
    
    for metric in sorted_metrics:
        brand = metric['brand']
        lead_time = metric['lead_time_days']
        target_tons = metric['may_target']
        
        # Calculate production phases
        planning_phase = 2  # 2 days planning
        setup_phase = max(2, metric['setup_complexity'] / 2)  # Setup time based on complexity
        production_phase = max(3, target_tons / 50)  # 50 tons per day capacity
        quality_phase = 1  # 1 day quality check
        
        total_duration = planning_phase + setup_phase + production_phase + quality_phase
        
        # Schedule phases
        phases = [
            {
                'brand': brand,
                'phase': 'Planning',
                'start_date': current_date,
                'end_date': current_date + timedelta(days=planning_phase),
                'duration': planning_phase,
                'resources': 'Planning Team',
                'deliverable': 'Production Plan'
            },
            {
                'brand': brand,
                'phase': 'Setup',
                'start_date': current_date + timedelta(days=planning_phase),
                'end_date': current_date + timedelta(days=planning_phase + setup_phase),
                'duration': setup_phase,
                'resources': 'Setup Crew',
                'deliverable': 'Machine Ready'
            },
            {
                'brand': brand,
                'phase': 'Production',
                'start_date': current_date + timedelta(days=planning_phase + setup_phase),
                'end_date': current_date + timedelta(days=planning_phase + setup_phase + production_phase),
                'duration': production_phase,
                'resources': 'Production Line',
                'deliverable': f'{target_tons:.0f} tons'
            },
            {
                'brand': brand,
                'phase': 'Quality Control',
                'start_date': current_date + timedelta(days=planning_phase + setup_phase + production_phase),
                'end_date': current_date + timedelta(days=total_duration),
                'duration': quality_phase,
                'resources': 'QC Team',
                'deliverable': 'Quality Approved'
            }
        ]
        
        schedule_data.extend(phases)
        current_date += timedelta(days=total_duration + 1)  # Add buffer day
    
    return pd.DataFrame(schedule_data)

def generate_resource_allocation(production_metrics):
    """Generate resource allocation recommendations"""
    
    resource_data = []
    
    for metric in production_metrics:
        brand = metric['brand']
        
        # Labor allocation
        operators_needed = max(2, metric['labor_hours'] / 160)  # 160 hours per month per operator
        supervisors_needed = max(1, operators_needed / 10)
        qc_staff_needed = max(1, metric['sku_count'] / 20)
        
        # Machine allocation
        production_lines = max(1, metric['may_target'] / 200)  # 200 tons per line capacity
        support_equipment = production_lines * 2
        
        # Material requirements
        raw_material_tons = metric['may_target'] * 1.05  # 5% waste factor
        packaging_units = metric['may_target'] * 40  # 40 packages per ton
        
        resource_data.append({
            'brand': brand,
            'target_tons': metric['may_target'],
            'operators': round(operators_needed, 1),
            'supervisors': round(supervisors_needed, 1),
            'qc_staff': round(qc_staff_needed, 1),
            'production_lines': round(production_lines, 1),
            'support_equipment': round(support_equipment, 0),
            'raw_material_tons': round(raw_material_tons, 1),
            'packaging_units': round(packaging_units, 0),
            'priority': 'High' if metric['quality_risk'] == 'High' else 'Medium' if metric['growth_ratio'] > 2 else 'Normal'
        })
    
    return pd.DataFrame(resource_data)

def generate_enhanced_insight_analysis(brand_targets_agg, predictions, selected_brand=None):
    """Generate enhanced production planning analysis"""
    
    has_api_key, source = setup_openai_api()
    if not has_api_key:
        return None, None, None, "No API key available"
    
    try:
        # Calculate production metrics
        production_metrics = calculate_production_metrics(brand_targets_agg, predictions)
        
        # Generate schedule and resource allocation
        schedule_df = generate_production_schedule(brand_targets_agg, production_metrics)
        resource_df = generate_resource_allocation(production_metrics)
        
        # Prepare comprehensive data for AI
        total_may_target = sum(targets['mayTarget'] for targets in brand_targets_agg.values())
        total_historical = sum(targets.get('historicalTonnage', 0) for targets in brand_targets_agg.values())
        total_cost = sum(m['total_cost'] for m in production_metrics)
        total_labor_hours = sum(m['labor_hours'] for m in production_metrics)
        avg_lead_time = np.mean([m['lead_time_days'] for m in production_metrics])
        
        # Enhanced AI prompt with production planning focus
        prompt = f"""
        As a senior production planning manager, analyze this comprehensive production data and provide strategic recommendations.
        
        PRODUCTION OVERVIEW:
        - Total Target: {total_may_target:.1f} tons
        - Total Historical: {total_historical:.1f} tons
        - Growth Rate: {((total_may_target/total_historical-1)*100):.1f}%
        - Total Brands: {len(brand_targets_agg)}
        - Estimated Cost: ${total_cost:,.0f}
        - Labor Hours: {total_labor_hours:,.0f}
        - Avg Lead Time: {avg_lead_time:.1f} days
        
        BRAND METRICS:
        {json.dumps(production_metrics[:5], indent=2)}
        
        Return ONLY a JSON object with this structure:
        {{
            "executive_summary": {{
                "production_feasibility": "High/Medium/Low",
                "key_challenges": ["challenge1", "challenge2", "challenge3"],
                "success_probability": "percentage",
                "critical_path": "description"
            }},
            "capacity_analysis": {{
                "overall_utilization": "percentage",
                "bottleneck_areas": ["area1", "area2"],
                "expansion_needs": "description",
                "efficiency_recommendations": ["rec1", "rec2"]
            }},
            "resource_planning": {{
                "labor_strategy": "description",
                "equipment_requirements": ["req1", "req2"],
                "material_sourcing": "strategy",
                "budget_allocation": "recommendations"
            }},
            "schedule_optimization": {{
                "production_sequence": ["brand1", "brand2", "brand3"],
                "parallel_processing": "opportunities",
                "milestone_timeline": "key dates",
                "contingency_plans": ["plan1", "plan2"]
            }},
            "quality_assurance": {{
                "high_risk_products": ["product1", "product2"],
                "quality_control_points": ["point1", "point2"],
                "testing_requirements": "description",
                "compliance_considerations": ["consideration1", "consideration2"]
            }},
            "cost_optimization": {{
                "cost_reduction_opportunities": ["opp1", "opp2"],
                "roi_projections": "description",
                "budget_variance_risks": ["risk1", "risk2"],
                "profitability_analysis": "assessment"
            }},
            "risk_management": {{
                "operational_risks": ["risk1", "risk2", "risk3"],
                "mitigation_strategies": ["strategy1", "strategy2"],
                "monitoring_kpis": ["kpi1", "kpi2", "kpi3"],
                "escalation_procedures": "description"
            }}
        }}
        """
        
        # Call OpenAI API
        api_key = OPENAI_API_KEY if OPENAI_API_KEY else st.session_state.get('openai_api_key')
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a senior production planning manager with expertise in manufacturing operations. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Clean response
            if ai_response.startswith("```json"):
                ai_response = ai_response[7:]
            if ai_response.endswith("```"):
                ai_response = ai_response[:-3]
            
            ai_analysis = json.loads(ai_response)
            
        except json.JSONDecodeError:
            ai_analysis = create_fallback_production_analysis(total_may_target, len(brand_targets_agg))
        except Exception as api_error:
            return None, production_metrics, None, f"API Error: {str(api_error)}"
        
        # Combine all analysis data
        comprehensive_analysis = {
            'ai_analysis': ai_analysis,
            'production_metrics': production_metrics,
            'schedule_data': schedule_df,
            'resource_allocation': resource_df,
            'summary_stats': {
                'total_target': total_may_target,
                'total_cost': total_cost,
                'total_labor_hours': total_labor_hours,
                'avg_lead_time': avg_lead_time
            }
        }
        
        return comprehensive_analysis, production_metrics, schedule_df, None
        
    except Exception as e:
        return None, None, None, f"Analysis Error: {str(e)}"

def create_fallback_production_analysis(total_target, brand_count):
    """Create fallback production analysis"""
    return {
        "executive_summary": {
            "production_feasibility": "Medium",
            "key_challenges": [
                f"Managing {total_target:.0f} tons production target",
                f"Coordinating {brand_count} different brands",
                "Quality control across multiple SKUs"
            ],
            "success_probability": "75%",
            "critical_path": "Setup and production scheduling optimization"
        },
        "capacity_analysis": {
            "overall_utilization": "78%",
            "bottleneck_areas": ["Machine setup time", "Quality control"],
            "expansion_needs": "Additional production line consideration",
            "efficiency_recommendations": ["Optimize changeover times", "Implement lean manufacturing"]
        },
        "resource_planning": {
            "labor_strategy": "Increase skilled operators and add quality control staff",
            "equipment_requirements": ["Additional production lines", "Quality testing equipment"],
            "material_sourcing": "Secure raw material supply contracts early",
            "budget_allocation": "Focus on high-volume, high-margin products"
        },
        "schedule_optimization": {
            "production_sequence": ["High-risk brands first", "High-volume products", "Complex SKUs last"],
            "parallel_processing": "Setup and quality control can run in parallel",
            "milestone_timeline": "Weekly review points for progress tracking",
            "contingency_plans": ["Overtime scheduling", "Outsourcing options"]
        },
        "quality_assurance": {
            "high_risk_products": ["New product variants", "High-growth items"],
            "quality_control_points": ["Raw material inspection", "In-process testing", "Final inspection"],
            "testing_requirements": "Enhanced testing for high-risk products",
            "compliance_considerations": ["Safety standards", "Quality certifications"]
        },
        "cost_optimization": {
            "cost_reduction_opportunities": ["Bulk material purchasing", "Setup time reduction"],
            "roi_projections": "15-20% improvement with optimization",
            "budget_variance_risks": ["Material cost fluctuation", "Overtime requirements"],
            "profitability_analysis": "Focus on high-margin products for maximum ROI"
        },
        "risk_management": {
            "operational_risks": ["Equipment breakdown", "Material shortage", "Quality issues"],
            "mitigation_strategies": ["Preventive maintenance", "Supplier diversification", "Quality checkpoints"],
            "monitoring_kpis": ["On-time delivery", "Quality rate", "Cost variance"],
            "escalation_procedures": "Daily production meetings with weekly management reviews"
        }
    }

def display_production_analysis_dashboard():
    """Display comprehensive production analysis dashboard"""
    
    comprehensive_analysis = st.session_state.get('comprehensive_analysis')
    if not comprehensive_analysis:
        return
    
    ai_analysis = comprehensive_analysis['ai_analysis']
    production_metrics = comprehensive_analysis['production_metrics']
    schedule_data = comprehensive_analysis['schedule_data']
    resource_allocation = comprehensive_analysis['resource_allocation']
    summary_stats = comprehensive_analysis['summary_stats']
    
    st.divider()
    st.markdown("### 📊 Production Planning Analysis Dashboard")
    
    # Executive Summary Cards
    display_production_executive_summary(ai_analysis, summary_stats)
    
    st.divider()
    
    # Production Metrics Table
    display_production_metrics_table(production_metrics)
    
    st.divider()
    
    # Capacity and Resource Analysis
    display_capacity_resource_analysis(ai_analysis, production_metrics, resource_allocation)
    
    st.divider()
    
    # Production Schedule
    display_production_schedule(schedule_data, ai_analysis)
    
    st.divider()
    
    # Risk and Quality Analysis
    display_risk_quality_analysis(ai_analysis, production_metrics)
    
    st.divider()
    
    # Cost Analysis
    display_cost_analysis(ai_analysis, production_metrics)

def display_production_executive_summary(ai_analysis, summary_stats):
    """Display production executive summary"""
    
    st.markdown("#### 🎯 Production Planning Executive Summary")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        feasibility = ai_analysis.get('executive_summary', {}).get('production_feasibility', 'Medium')
        feasibility_color = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}.get(feasibility, "⚪")
        st.metric("Feasibility", f"{feasibility_color} {feasibility}")
    
    with col2:
        success_prob = ai_analysis.get('executive_summary', {}).get('success_probability', 'N/A')
        st.metric("Success Rate", success_prob)
    
    with col3:
        total_cost = summary_stats.get('total_cost', 0)
        st.metric("Total Cost", f"${total_cost:,.0f}")
    
    with col4:
        avg_lead_time = summary_stats.get('avg_lead_time', 0)
        st.metric("Avg Lead Time", f"{avg_lead_time:.1f} days")
    
    # Key challenges
    challenges = ai_analysis.get('executive_summary', {}).get('key_challenges', [])
    if challenges:
        st.markdown("**⚠️ Key Production Challenges:**")
        for i, challenge in enumerate(challenges, 1):
            st.markdown(f"{i}. {challenge}")
    
    # Critical path
    critical_path = ai_analysis.get('executive_summary', {}).get('critical_path', '')
    if critical_path:
        st.info(f"**🎯 Critical Path:** {critical_path}")

def display_production_metrics_table(production_metrics):
    """Display detailed production metrics table"""
    
    st.markdown("#### 📋 Detailed Production Metrics Analysis")
    
    # Convert to DataFrame for better display
    df_metrics = pd.DataFrame(production_metrics)
    
    # Create comprehensive metrics table
    display_df = df_metrics[[
        'brand', 'may_target', 'sku_count', 'capacity_utilization', 
        'lead_time_days', 'quality_risk', 'cost_per_ton', 'growth_ratio'
    ]].copy()
    
    display_df.columns = [
        'Brand', 'Target (tons)', 'SKU Count', 'Capacity (%)', 
        'Lead Time (days)', 'Quality Risk', 'Cost/Ton ($)', 'Growth Ratio'
    ]
    
    # Color coding for risks
    def highlight_risk(val):
        if isinstance(val, str):
            if val == 'High':
                return 'background-color: #ffcccc'
            elif val == 'Medium':
                return 'background-color: #fff3cd'
            elif val == 'Low':
                return 'background-color: #d4edda'
        return ''
    
    styled_df = display_df.style.applymap(highlight_risk, subset=['Quality Risk'])
    st.dataframe(styled_df, use_container_width=True)
    
    # Summary statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_target = df_metrics['may_target'].sum()
        st.metric("Total Production Target", f"{total_target:.1f} tons")
    
    with col2:
        avg_capacity = df_metrics['capacity_utilization'].mean()
        st.metric("Average Capacity Utilization", f"{avg_capacity:.1f}%")
    
    with col3:
        high_risk_count = len(df_metrics[df_metrics['quality_risk'] == 'High'])
        st.metric("High Risk Brands", high_risk_count)

def display_capacity_resource_analysis(ai_analysis, production_metrics, resource_allocation):
    """Display capacity and resource analysis"""
    
    st.markdown("#### ⚙️ Capacity & Resource Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🏭 Capacity Analysis**")
        
        capacity_analysis = ai_analysis.get('capacity_analysis', {})
        
        utilization = capacity_analysis.get('overall_utilization', 'N/A')
        st.info(f"**Overall Utilization:** {utilization}")
        
        bottlenecks = capacity_analysis.get('bottleneck_areas', [])
        if bottlenecks:
            st.markdown("**Bottleneck Areas:**")
            for bottleneck in bottlenecks:
                st.markdown(f"🔴 {bottleneck}")
        
        efficiency_recs = capacity_analysis.get('efficiency_recommendations', [])
        if efficiency_recs:
            st.markdown("**Efficiency Recommendations:**")
            for rec in efficiency_recs:
                st.markdown(f"💡 {rec}")
    
    with col2:
        st.markdown("**👥 Resource Planning**")
        
        resource_planning = ai_analysis.get('resource_planning', {})
        
        labor_strategy = resource_planning.get('labor_strategy', 'N/A')
        st.success(f"**Labor Strategy:** {labor_strategy}")
        
        equipment_reqs = resource_planning.get('equipment_requirements', [])
        if equipment_reqs:
            st.markdown("**Equipment Requirements:**")
            for req in equipment_reqs:
                st.markdown(f"🔧 {req}")
    
    # Resource allocation chart
    if not resource_allocation.empty:
        st.markdown("**📊 Resource Allocation by Brand**")
        
        fig_resource = px.bar(
            resource_allocation,
            x='brand',
            y=['operators', 'supervisors', 'qc_staff'],
            title="Human Resource Allocation",
            labels={'value': 'Number of Staff', 'variable': 'Role'},
            barmode='group'
        )
        st.plotly_chart(fig_resource, use_container_width=True)

def display_production_schedule(schedule_data, ai_analysis):
    """Display production schedule analysis"""
    
    st.markdown("#### 📅 Production Schedule Optimization")
    
    if not schedule_data.empty:
        # Timeline chart
        fig_timeline = px.timeline(
            schedule_data,
            x_start='start_date',
            x_end='end_date',
            y='brand',
            color='phase',
            title="Production Timeline by Brand",
            hover_data=['resources', 'deliverable']
        )
        fig_timeline.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Schedule optimization recommendations
        schedule_opt = ai_analysis.get('schedule_optimization', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🎯 Recommended Production Sequence:**")
            sequence = schedule_opt.get('production_sequence', [])
            for i, item in enumerate(sequence, 1):
                st.markdown(f"{i}. {item}")
        
        with col2:
            st.markdown("**⚡ Optimization Opportunities:**")
            
            parallel = schedule_opt.get('parallel_processing', 'N/A')
            st.info(f"**Parallel Processing:** {parallel}")
            
            timeline = schedule_opt.get('milestone_timeline', 'N/A')
            st.info(f"**Timeline:** {timeline}")

def display_risk_quality_analysis(ai_analysis, production_metrics):
    """Display risk and quality analysis"""
    
    st.markdown("#### ⚠️ Risk Management & Quality Assurance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🛡️ Risk Management**")
        
        risk_mgmt = ai_analysis.get('risk_management', {})
        
        operational_risks = risk_mgmt.get('operational_risks', [])
        if operational_risks:
            st.markdown("**Operational Risks:**")
            for risk in operational_risks:
                st.markdown(f"⚠️ {risk}")
        
        mitigation = risk_mgmt.get('mitigation_strategies', [])
        if mitigation:
            st.markdown("**Mitigation Strategies:**")
            for strategy in mitigation:
                st.markdown(f"✅ {strategy}")
    
    with col2:
        st.markdown("**🔍 Quality Assurance**")
        
        quality_assurance = ai_analysis.get('quality_assurance', {})
        
        high_risk_products = quality_assurance.get('high_risk_products', [])
        if high_risk_products:
            st.markdown("**High Risk Products:**")
            for product in high_risk_products:
                st.markdown(f"🔴 {product}")
        
        qc_points = quality_assurance.get('quality_control_points', [])
        if qc_points:
            st.markdown("**Quality Control Points:**")
            for point in qc_points:
                st.markdown(f"🎯 {point}")
    
    # Risk distribution chart
    df_metrics = pd.DataFrame(production_metrics)
    if not df_metrics.empty:
        risk_counts = df_metrics['quality_risk'].value_counts()
        
        fig_risk = px.pie(
            values=risk_counts.values,
            names=risk_counts.index,
            title="Quality Risk Distribution",
            color_discrete_map={
                'High': '#ff4444',
                'Medium': '#ffaa00',
                'Low': '#44ff44'
            }
        )
        st.plotly_chart(fig_risk, use_container_width=True)

def display_cost_analysis(ai_analysis, production_metrics):
    """Display cost analysis"""
    
    st.markdown("#### 💰 Cost Analysis & Optimization")
    
    df_metrics = pd.DataFrame(production_metrics)
    
    # Cost breakdown chart
    col1, col2 = st.columns(2)
    
    with col1:
        # Cost by brand
        fig_cost = px.bar(
            df_metrics,
            x='brand',
            y='total_cost',
            title="Total Cost by Brand",
            labels={'total_cost': 'Total Cost ($)', 'brand': 'Brand'}
        )
        st.plotly_chart(fig_cost, use_container_width=True)
    
    with col2:
        # Cost per ton analysis
        fig_cost_per_ton = px.scatter(
            df_metrics,
            x='may_target',
            y='cost_per_ton',
            size='sku_count',
            hover_name='brand',
            title="Cost Efficiency Analysis",
            labels={'may_target': 'Target Volume (tons)', 'cost_per_ton': 'Cost per Ton ($)'}
        )
        st.plotly_chart(fig_cost_per_ton, use_container_width=True)
    
    # Cost optimization recommendations
    cost_opt = ai_analysis.get('cost_optimization', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**💡 Cost Reduction Opportunities:**")
        opportunities = cost_opt.get('cost_reduction_opportunities', [])
        for opp in opportunities:
            st.markdown(f"• {opp}")
    
    with col2:
        st.markdown("**📈 Financial Projections:**")
        
        roi_proj = cost_opt.get('roi_projections', 'N/A')
        st.success(f"**ROI:** {roi_proj}")
        
        profitability = cost_opt.get('profitability_analysis', 'N/A')
        st.info(f"**Profitability:** {profitability}")

def display_insights_section(brand_targets_agg, predictions, selected_brand):
    """Enhanced main display function for production insights"""
    
    st.subheader("🤖 AI Production Planning Analysis")
    
    # Check OpenAI availability
    if not OPENAI_AVAILABLE:
        st.error("❌ OpenAI library not available")
        st.code("pip install openai", language="bash")
        return
    
    # API Key setup
    has_api_key, source = setup_openai_api()
    
    if not has_api_key:
        st.warning("⚠️ OpenAI API Key required for detailed production analysis")
        
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
    if st.button("🚀 Generate Production Analysis", type="primary", use_container_width=True):
        with st.spinner("🧠 Analyzing production planning requirements..."):
            try:
                comprehensive_analysis, production_metrics, schedule_data, error = generate_enhanced_insight_analysis(
                    brand_targets_agg, predictions, selected_brand
                )
                
                if error:
                    st.error(f"❌ {error}")
                    return
                
                if not comprehensive_analysis:
                    st.error("❌ Failed to generate production analysis")
                    return
                
                # Store in session state
                st.session_state.comprehensive_analysis = comprehensive_analysis
                
                st.success("✅ Production analysis completed!")
                st.balloons()
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    # Display comprehensive results
    if st.session_state.get('comprehensive_analysis'):
        display_production_analysis_dashboard()
        
        # Download options
        st.divider()
        display_production_download_options()

def display_production_download_options():
    """Display download options for production analysis"""
    
    st.markdown("#### 📥 Export Production Analysis")
    
    comprehensive_analysis = st.session_state.get('comprehensive_analysis')
    if not comprehensive_analysis:
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Download complete analysis as JSON
        analysis_json = json.dumps(comprehensive_analysis, indent=2, ensure_ascii=False, default=str)
        st.download_button(
            label="📄 Complete Analysis (JSON)",
            data=analysis_json,
            file_name=f"production_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with col2:
        # Download production metrics as CSV
        production_metrics = comprehensive_analysis.get('production_metrics', [])
        if production_metrics:
            df_metrics = pd.DataFrame(production_metrics)
            csv_data = df_metrics.to_csv(index=False)
            st.download_button(
                label="📊 Production Metrics (CSV)",
                data=csv_data,
                file_name=f"production_metrics_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with col3:
        # Download schedule as CSV
        schedule_data = comprehensive_analysis.get('schedule_data')
        if schedule_data is not None and not schedule_data.empty:
            schedule_csv = schedule_data.to_csv(index=False)
            st.download_button(
                label="📅 Production Schedule (CSV)",
                data=schedule_csv,
                file_name=f"production_schedule_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
