import plotly.graph_objects as go
# We need this helper to normalize scores for the graphs
from mbti import align_scores_with_mbti

# ==========================================
# 1. Original Spectrum Chart (Dot Plot)
# ==========================================
def generate_bipolar_chart(analysis_results):
    try:
        dimensions = [
            {"label": "Energy", "left": "Introversion (I)", "right": "Extraversion (E)", "y": 0},
            {"label": "Info", "left": "Sensing (S)", "right": "Intuition (N)", "y": 1},
            {"label": "Decisions", "left": "Thinking (T)", "right": "Feeling (F)", "y": 2},
            {"label": "Lifestyle", "left": "Judging (J)", "right": "Perceiving (P)", "y": 3}
        ]
        
        fig = go.Figure()
        
        # Draw background lines
        for dim in dimensions:
            fig.add_shape(type="line", x0=0, y0=dim['y'], x1=100, y1=dim['y'], 
                         line=dict(color="#E0E0E0", width=4))
            fig.add_annotation(x=-5, y=dim['y'], text=dim['left'], showarrow=False, xanchor="right")
            fig.add_annotation(x=105, y=dim['y'], text=dim['right'], showarrow=False, xanchor="left")
        
        colors = ['#FF69B4', '#1E90FF', '#32CD32', '#FFA500', '#9370DB', '#DC143C', '#00CED1']
        
        for i, person in enumerate(analysis_results):
            # Ensure we get [E, N, F, P] scores normalized
            scores = align_scores_with_mbti(person['mbti'], person['scores'])
            color = colors[i % len(colors)]
            
            fig.add_trace(go.Scatter(
                x=scores, y=[0,1,2,3], mode='markers+text', 
                name=f"{person['name']} ({person['mbti']})",
                marker=dict(size=18, color=color, line=dict(width=2, color='white')),
                text=scores, textposition="top center",
                textfont=dict(color=color, weight='bold')
            ))
            
        fig.update_layout(
            title="✨ Personality Spectrum",
            height=400, showlegend=True,
            xaxis=dict(range=[-20, 120], showgrid=False, visible=False),
            yaxis=dict(range=[-0.5, 3.5], showgrid=False, visible=False),
            margin=dict(l=100, r=100, t=50, b=20),
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig
    except Exception as e:
        print(f"Chart Error: {e}")
        return go.Figure()

# ==========================================
# 2. Group Bar Chart (Histogram Style)
# ==========================================
def generate_group_bar_chart(analysis_results):
    try:
        fig = go.Figure()
        traits = ['E/I (Energy)', 'S/N (Info)', 'T/F (Decisions)', 'J/P (Lifestyle)']
        colors = ['#FF69B4', '#1E90FF', '#32CD32', '#FFA500', '#9370DB']

        for i, person in enumerate(analysis_results):
            scores = align_scores_with_mbti(person['mbti'], person['scores'])
            fig.add_trace(go.Bar(
                name=f"{person['name']} ({person['mbti']})",
                x=traits,
                y=scores,
                marker_color=colors[i % len(colors)]
            ))

        fig.update_layout(
            title="📊 Trait Intensity Comparison",
            barmode='group',
            height=400,
            yaxis=dict(title='Intensity % (Right Side Trait)', range=[0, 100]),
            plot_bgcolor='rgba(255,255,255,0.1)'
        )
        return fig
    except Exception as e:
        print(f"Bar Chart Error: {e}")
        return go.Figure()

# ==========================================
# 3. Radar Chart (Spider Web)
# ==========================================
def generate_radar_chart(analysis_results):
    try:
        fig = go.Figure()
        categories = ['Extraversion', 'Intuition', 'Feeling', 'Perceiving']
        colors = ['rgba(255, 105, 180, 0.5)', 'rgba(30, 144, 255, 0.5)', 'rgba(50, 205, 50, 0.5)']
        line_colors = ['#FF69B4', '#1E90FF', '#32CD32']

        for i, person in enumerate(analysis_results):
            scores = align_scores_with_mbti(person['mbti'], person['scores'])
            
            # Close the loop
            r_val = scores + [scores[0]]
            theta_val = categories + [categories[0]]
            
            fig.add_trace(go.Scatterpolar(
                r=r_val,
                theta=theta_val,
                fill='toself',
                name=person['name'],
                line_color=line_colors[i % len(line_colors)],
                fillcolor=colors[i % len(colors)]
            ))

        fig.update_layout(
            title="🕸️ Personality Shape",
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100])
            ),
            showlegend=True,
            height=400
        )
        return fig
    except Exception as e:
        print(f"Radar Chart Error: {e}")
        return go.Figure()