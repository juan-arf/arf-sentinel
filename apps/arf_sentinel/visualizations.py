import plotly.graph_objects as go

def risk_comparison_chart(agent_confidence: float, arf_risk: float) -> go.Figure:
    fig = go.Figure(data=[
        go.Bar(name='Agent Confidence', x=['Confidence / Risk'], y=[agent_confidence],
               marker_color='#9b59b6', text=f'{agent_confidence:.0%}', textposition='auto'),
        go.Bar(name='ARF Risk Posterior', x=['Confidence / Risk'], y=[arf_risk],
               marker_color='#e74c3c', text=f'{arf_risk:.0%}', textposition='auto')
    ])
    fig.update_layout(barmode='group', template='plotly_dark',
                      title='Confidence ≠ Execution Safety',
                      yaxis=dict(range=[0,1]))
    return fig

def expected_loss_chart(losses: dict) -> go.Figure:
    actions = list(losses.keys())
    values = list(losses.values())
    min_val = min(values)
    colors = ['#2E86AB' if v != min_val else '#00FF88' for v in values]
    fig = go.Figure(data=[go.Bar(x=actions, y=values, marker_color=colors)])
    fig.update_layout(title='Expected Loss by Decision',
                      yaxis_title='Expected Loss',
                      template='plotly_dark', height=400)
    return fig

def blast_radius_treemap(affected: int, direct: int, transitive: int) -> go.Figure:
    labels = ['Affected Repos', 'Direct Dependencies', 'Transitive Dependencies']
    parents = ['', 'Affected Repos', 'Affected Repos']
    values = [affected, direct, transitive]
    colors = ['#00bcd4', '#9b59b6', '#e74c3c']
    fig = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values,
        marker=dict(colors=colors),
        textinfo='label+value'
    ))
    fig.update_layout(title='Blast Radius Composition', template='plotly_dark', height=400)
    return fig
