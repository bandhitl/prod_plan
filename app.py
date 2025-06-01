# Safe AI Analysis - เพิ่ม functions เหล่านี้ในไฟล์หลัก (ไม่แทนที่อะไร)
# แค่เพิ่มที่ท้ายไฟล์ก่อน st.divider() บรรทัดสุดท้าย

def generate_simple_ai_insights(brand_targets_agg, predictions):
    """Generate simple AI insights without complex processing"""
    try:
        # Basic calculations
        total_may_target = sum(targets['mayTarget'] for targets in brand_targets_agg.values())
        total_historical = sum(targets.get('historicalTonnage', 0) for targets in brand_targets_agg.values())
        growth_rate = (total_may_target / total_historical - 1) * 100 if total_historical > 0 else 0
        
        # Brand analysis
        brand_analysis = []
        for brand, targets in brand_targets_agg.items():
            historical = targets.get('historicalTonnage', 0)
            may_target = targets['mayTarget']
            brand_growth = (may_target / historical - 1) * 100 if historical > 0 else 0
            
            # Simple risk assessment
            if brand_growth > 200:  # 3x growth
                risk_level = "High"
            elif brand_growth > 50:  # 1.5x growth
                risk_level = "Medium"
            else:
                risk_level = "Low"
            
            # SKU count
            sku_count = len(predictions.get(brand, {}).get('mayDistribution', {}))
            
            brand_analysis.append({
                'brand': brand,
                'target': may_target,
                'growth_pct': brand_growth,
                'risk_level': risk_level,
                'sku_count': sku_count
            })
        
        return {
            'total_target': total_may_target,
            'total_historical': total_historical,
            'overall_growth': growth_rate,
            'brand_count': len(brand_analysis),
            'brand_analysis': brand_analysis
        }
    
    except Exception as e:
        st.error(f"Error in analysis: {e}")
        return None

def display_simple_ai_analysis():
    """Display simple AI analysis results"""
    
    if not st.session_state.get('simple_ai_results'):
        return
    
    results = st.session_state.simple_ai_results
    
    st.markdown("### 📊 Production Analysis Results")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Target", f"{results['total_target']:.1f} tons")
    
    with col2:
        st.metric("Growth Rate", f"{results['overall_growth']:.1f}%")
    
    with col3:
        st.metric("Brand Count", results['brand_count'])
    
    with col4:
        high_risk_count = len([b for b in results['brand_analysis'] if b['risk_level'] == 'High'])
        st.metric("High Risk Brands", high_risk_count)
    
    # Brand analysis table
    st.markdown("#### 📋 Brand Analysis")
    
    df_brands = pd.DataFrame(results['brand_analysis'])
    
    if not df_brands.empty:
        # Rename columns for display
        display_df = df_brands.copy()
        display_df = display_df.rename(columns={
            'brand': 'Brand',
            'target': 'Target (tons)',
            'growth_pct': 'Growth (%)',
            'risk_level': 'Risk Level',
            'sku_count': 'SKU Count'
        })
        
        st.dataframe(display_df, use_container_width=True)
        
        # Simple visualization
        col1, col2 = st.columns(2)
        
        with col1:
            # Risk distribution
            risk_counts = df_brands['risk_level'].value_counts()
            fig_risk = px.pie(
                values=risk_counts.values,
                names=risk_counts.index,
                title="Risk Level Distribution",
                color_discrete_map={
                    'High': '#ff4444',
                    'Medium': '#ffaa00',
                    'Low': '#44ff44'
                }
            )
            st.plotly_chart(fig_risk, use_container_width=True)
        
        with col2:
            # Growth vs Target
            fig_growth = px.scatter(
                df_brands,
                x='target',
                y='growth_pct',
                color='risk_level',
                size='sku_count',
                hover_name='brand',
                title="Target vs Growth Analysis",
                labels={'target': 'Target (tons)', 'growth_pct': 'Growth (%)'},
                color_discrete_map={
                    'High': '#ff4444',
                    'Medium': '#ffaa00',
                    'Low': '#44ff44'
                }
            )
            st.plotly_chart(fig_growth, use_container_width=True)

def call_openai_api_safely(brand_targets_agg, predictions):
    """Safely call OpenAI API with comprehensive error handling"""
    
    # Check API availability
    has_api_key, source = setup_openai_api()
    if not has_api_key:
        return None, "No API key available"
    
    try:
        # Get API key
        api_key = OPENAI_API_KEY if OPENAI_API_KEY else st.session_state.get('openai_api_key')
        
        if not api_key:
            return None, "API Key not found"
        
        # Prepare simple data summary
        total_target = sum(targets['mayTarget'] for targets in brand_targets_agg.values())
        brand_count = len(brand_targets_agg)
        high_growth_brands = []
        
        for brand, targets in brand_targets_agg.items():
            historical = targets.get('historicalTonnage', 0)
            if historical > 0 and targets['mayTarget'] / historical > 3:
                high_growth_brands.append(brand)
        
        # Simple AI prompt
        prompt = f"""
        Analyze this production planning scenario and provide brief recommendations:
        
        - Total production target: {total_target:.0f} tons
        - Number of brands: {brand_count}
        - High growth brands: {len(high_growth_brands)}
        
        Provide a JSON response with:
        {{
            "feasibility": "High/Medium/Low",
            "key_recommendations": ["rec1", "rec2", "rec3"],
            "main_challenges": ["challenge1", "challenge2"],
            "success_tips": ["tip1", "tip2", "tip3"]
        }}
        """
        
        # Call OpenAI API with timeout and error handling
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a production planning expert. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.3
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Clean and parse response
        if ai_response.startswith("```json"):
            ai_response = ai_response[7:]
        if ai_response.endswith("```"):
            ai_response = ai_response[:-3]
        
        ai_result = json.loads(ai_response)
        return ai_result, None
        
    except json.JSONDecodeError:
        return None, "Failed to parse AI response"
    except Exception as e:
        return None, f"API Error: {str(e)}"

def display_ai_recommendations():
    """Display AI recommendations if available"""
    
    if not st.session_state.get('ai_recommendations'):
        return
    
    ai_recs = st.session_state.ai_recommendations
    
    st.markdown("### 🤖 AI Recommendations")
    
    # Feasibility assessment
    feasibility = ai_recs.get('feasibility', 'Unknown')
    if feasibility == 'High':
        st.success(f"✅ Production Feasibility: {feasibility}")
    elif feasibility == 'Medium':
        st.warning(f"⚠️ Production Feasibility: {feasibility}")
    else:
        st.error(f"❌ Production Feasibility: {feasibility}")
    
    # Recommendations in columns
    col1, col2 = st.columns(2)
    
    with col1:
        recommendations = ai_recs.get('key_recommendations', [])
        if recommendations:
            st.markdown("**💡 Key Recommendations:**")
            for rec in recommendations:
                st.markdown(f"• {rec}")
        
        success_tips = ai_recs.get('success_tips', [])
        if success_tips:
            st.markdown("**🎯 Success Tips:**")
            for tip in success_tips:
                st.markdown(f"• {tip}")
    
    with col2:
        challenges = ai_recs.get('main_challenges', [])
        if challenges:
            st.markdown("**⚠️ Main Challenges:**")
            for challenge in challenges:
                st.markdown(f"• {challenge}")

# แก้ไข function หลัก display_insights_section ให้เรียบง่าย
def display_insights_section_safe(brand_targets_agg, predictions, selected_brand):
    """Safe version of insights section"""
    
    st.subheader("🤖 AI Production Analysis")
    
    # Basic Analysis Button
    if st.button("📊 Generate Basic Analysis", type="secondary", use_container_width=True):
        with st.spinner("Calculating..."):
            try:
                results = generate_simple_ai_insights(brand_targets_agg, predictions)
                if results:
                    st.session_state.simple_ai_results = results
                    st.success("✅ Basic analysis completed!")
                else:
                    st.error("❌ Failed to generate analysis")
            except Exception as e:
                st.error(f"Error: {e}")
    
    # Display basic results
    if st.session_state.get('simple_ai_results'):
        display_simple_ai_analysis()
    
    # Advanced AI Analysis
    st.divider()
    
    # Check for OpenAI
    if OPENAI_AVAILABLE:
        st.markdown("#### 🤖 Advanced AI Analysis")
        
        # API Key input
        if 'openai_api_key' not in st.session_state:
            st.session_state.openai_api_key = ""
        
        api_key = st.text_input(
            "OpenAI API Key (optional):",
            value=st.session_state.openai_api_key,
            type="password",
            help="Enter your OpenAI API key for AI recommendations"
        )
        st.session_state.openai_api_key = api_key
        
        # Advanced analysis button
        if st.button("🧠 Get AI Recommendations", 
                    type="primary", 
                    use_container_width=True,
                    disabled=not api_key):
            
            with st.spinner("AI is analyzing..."):
                try:
                    ai_result, error = call_openai_api_safely(brand_targets_agg, predictions)
                    
                    if error:
                        st.error(f"❌ {error}")
                    elif ai_result:
                        st.session_state.ai_recommendations = ai_result
                        st.success("✅ AI analysis completed!")
                    else:
                        st.warning("⚠️ No AI response received")
                        
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        
        # Display AI recommendations
        if st.session_state.get('ai_recommendations'):
            display_ai_recommendations()
    
    else:
        st.info("💡 Install OpenAI library for advanced AI analysis: `pip install openai`")
    
    # Download options
    if st.session_state.get('simple_ai_results') or st.session_state.get('ai_recommendations'):
        st.divider()
        st.markdown("#### 📥 Download Results")
        
        # Prepare download data
        download_data = {}
        if st.session_state.get('simple_ai_results'):
            download_data['basic_analysis'] = st.session_state.simple_ai_results
        if st.session_state.get('ai_recommendations'):
            download_data['ai_recommendations'] = st.session_state.ai_recommendations
        
        if download_data:
            json_data = json.dumps(download_data, indent=2)
            st.download_button(
                label="📄 Download Analysis (JSON)",
                data=json_data,
                file_name=f"production_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

# วิธีการใช้งาน:
# 1. เพิ่ม functions ทั้งหมดข้างบนในไฟล์หลัก
# 2. ในส่วน Tab2 ที่เรียกใช้ display_insights_section() 
#    ให้เปลี่ยนเป็น display_insights_section_safe() แทน
