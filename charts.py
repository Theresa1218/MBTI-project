# visuals.py
import plotly.graph_objects as go

def align_scores_with_mbti(mbti_type, raw_scores):
    if not mbti_type or len(raw_scores) != 4:
        return [50, 50, 50, 50]
    
    mbti = mbti_type.upper()
    corrected = list(raw_scores)
    
    mapping = [('I','E'), ('S','N'), ('T','F'), ('J','P')]
    for i, (left, right) in enumerate(mapping):
        if left in mbti: corrected[i] = min(corrected[i], 45)
        elif right in mbti: corrected[i] = max(corrected[i], 55)
            
    return corrected

def draw_bipolar_chart(mbti_a, mbti_b, name_a, name_b, scores_a, scores_b):
   
    final_a = align_scores_with_mbti(mbti_a, scores_a)
    final_b = align_scores_with_mbti(mbti_b, scores_b)
    
    dimensions = [
        {"label": "Energy (能量方向)", "left": "I (內向)", "right": "E (外向)", "y": 0},
        {"label": "Information (資訊)", "left": "S (實感)", "right": "N (直覺)", "y": 1},
        {"label": "Decisions (決策)", "left": "T (思考)", "right": "F (情感)", "y": 2},
        {"label": "Lifestyle (生活)", "left": "J (判斷)", "right": "P (感知)", "y": 3}
    ]
    
    fig = go.Figure()
    
    for dim in dimensions:
        fig.add_shape(type="line", x0=0, y0=dim['y'], x1=100, y1=dim['y'], line=dict(color="#E0E0E0", width=6))
        fig.add_annotation(x=-5, y=dim['y'], text=dim['left'], showarrow=False, xanchor="right", font=dict(color="#666"))
        fig.add_annotation(x=105, y=dim['y'], text=dim['right'], showarrow=False, xanchor="left", font=dict(color="#666"))
    
    # User A point
    fig.add_trace(go.Scatter(
        x=final_a, y=[0,1,2,3], mode='markers+text', name=f'{name_a} ({mbti_a})',
        marker=dict(size=20, color='#FF69B4', line=dict(width=2, color='white')),
        text=final_a, textposition="top center"
    ))
    
    # User B point
    fig.add_trace(go.Scatter(
        x=final_b, y=[0,1,2,3], mode='markers+text', name=f'{name_b} ({mbti_b})',
        marker=dict(size=20, color='#1E90FF', line=dict(width=2, color='white')),
        text=final_b, textposition="bottom center"
    ))
    
    fig.update_layout(
        title=f"📊 {name_a} vs {name_b} 性格光譜對比",
        height=400,
        showlegend=True,
        xaxis=dict(range=[-20, 120], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=[-0.5, 3.5], showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=50, r=50, t=50, b=20)
    )
    
    return fig