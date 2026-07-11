"""
Plotly chart generators for the ARF Sentinel Streamlit demo.

These visualisations are designed to communicate the Bayesian governance
story to a hackathon audience in under 10 seconds per chart:

    - risk_comparison_chart   : "Agent confidence is not execution safety."
    - expected_loss_chart     : "ARF picks the action with minimum expected loss."
    - blast_radius_treemap    : "Here's the composition of the blast radius."

All charts use the dark cyberpunk theme and the ARF Sentinel brand colours:
    CRAFT cyan      #00bcd4
    Nemotron violet #9b59b6
    ARF acid green  #00FF88
    Risk magenta    #e74c3c

Mathematical context is included in each function docstring.
"""

import plotly.graph_objects as go
from typing import Dict


def risk_comparison_chart(agent_confidence: float, arf_risk: float) -> go.Figure:
    """
    Dual bar chart comparing the agent's self‑reported confidence
    against the ARF posterior risk estimate.

    This chart directly visualises the core ARF thesis:

        "An agent can be 92% confident and still be unsafe."

    The ARF risk posterior is computed via Bayesian updating:

        P(Risk | Evidence) ∝ P(Evidence | Risk) · P(Risk)

    where the prior risk is 0.5 (uninformed) and the evidence
    confidence acts as the likelihood multiplier.  The resulting
    posterior is typically higher than the agent's confidence
    when the blast radius is large, illustrating that confidence
    alone is an insufficient metric for autonomous execution.

    Parameters
    ----------
    agent_confidence : float
        Agent's self‑assessed confidence (e.g., 0.92).
    arf_risk : float
        ARF posterior risk probability (e.g., 0.82).

    Returns
    -------
    plotly.graph_objects.Figure
        Grouped bar chart with two bars.
    """
    fig = go.Figure(data=[
        go.Bar(
            name='Agent Confidence',
            x=['Confidence / Risk'],
            y=[agent_confidence],
            marker_color='#9b59b6',      # Nemotron violet
            text=f'{agent_confidence:.0%}',
            textposition='auto',
            hovertemplate='Agent self‑reported: %{y:.0%}<extra></extra>',
        ),
        go.Bar(
            name='ARF Risk Posterior',
            x=['Confidence / Risk'],
            y=[arf_risk],
            marker_color='#e74c3c',      # Risk magenta
            text=f'{arf_risk:.0%}',
            textposition='auto',
            hovertemplate='ARF Bayesian posterior: %{y:.0%}<extra></extra>',
        ),
    ])

    # Add a horizontal line showing the uninformed prior (0.5)
    fig.add_hline(
        y=0.5,
        line_dash='dot',
        line_color='#6c757d',
        annotation_text='Prior risk (0.5)',
        annotation_position='bottom right',
    )

    fig.update_layout(
        barmode='group',
        template='plotly_dark',
        title='Confidence ≠ Execution Safety',
        yaxis=dict(range=[0, 1], title='Probability'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        margin=dict(t=60, b=40),
        height=350,
    )
    return fig


def expected_loss_chart(losses: Dict[str, float]) -> go.Figure:
    """
    Bar chart of expected losses for the three governance actions.

    ARF computes the expected loss for each action:

        ExpectedLoss(APPROVE)  = R · cost(B)
        ExpectedLoss(DENY)     = (1−R) · C · cost_deny
        ExpectedLoss(ESCALATE) = policy_weight · (R · cost(B) + cost_escalate)

    The action with the minimum expected loss is selected, unless
    a policy rule forces an override.

    In the chart, the minimum loss bar is highlighted in ARF acid green
    (#00FF88), while the others are shown in a muted blue (#2E86AB).

    Parameters
    ----------
    losses : dict
        Dictionary mapping action names ('APPROVE', 'DENY', 'ESCALATE')
        to their expected loss values.

    Returns
    -------
    plotly.graph_objects.Figure
        Bar chart with the minimum loss highlighted.
    """
    actions = list(losses.keys())
    values = list(losses.values())
    min_val = min(values)

    # Annotate which action is selected
    selected_action = [a for a, v in losses.items() if v == min_val][0]

    colors = [
        '#00FF88' if v == min_val else '#2E86AB'  # acid green for minimum
        for v in values
    ]

    fig = go.Figure(data=[
        go.Bar(
            x=actions,
            y=values,
            marker_color=colors,
            text=[f'{v:.3f}' for v in values],
            textposition='auto',
            hovertemplate='Action: %{x}<br>Expected loss: %{y:.4f}<extra></extra>',
        )
    ])

    # Add annotation explaining the selection
    fig.add_annotation(
        x=actions.index(selected_action),
        y=min_val,
        text=f'ARF selects {selected_action}<br>(minimum loss)',
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=-40,
        font=dict(color='#00FF88', size=12),
    )

    fig.update_layout(
        title='Expected Loss by Decision (Bayesian Expected Loss Minimisation)',
        yaxis_title='Expected Loss',
        template='plotly_dark',
        height=400,
        xaxis=dict(categoryorder='total descending'),
        margin=dict(t=60, b=40),
    )
    return fig


def blast_radius_treemap(affected: int, direct: int, transitive: int) -> go.Figure:
    """
    Treemap showing the composition of the blast radius.

    The treemap breaks down the affected repositories into:

        - Affected Repos       (total count)
        - Direct Dependencies  (direct imports of the vulnerable package)
        - Transitive Dependencies (indirectly exposed through direct deps)

    This visualisation helps stakeholders understand where the risk
    originates – whether it's concentrated in a few direct dependencies
    or spread across a wide transitive network.

    The colours follow the ARF Sentinel brand:
        CRAFT cyan      for affected repos
        Nemotron violet for direct dependencies
        Risk magenta    for transitive dependencies

    Parameters
    ----------
    affected : int
        Total number of affected repositories.
    direct : int
        Number of direct dependencies.
    transitive : int
        Number of transitive dependencies.

    Returns
    -------
    plotly.graph_objects.Figure
        Treemap chart.
    """
    labels = [
        'Affected Repos',
        'Direct Dependencies',
        'Transitive Dependencies',
    ]
    parents = [
        '',                    # root
        'Affected Repos',      # direct under affected
        'Affected Repos',      # transitive under affected
    ]
    values = [affected, direct, transitive]
    colors = [
        '#00bcd4',   # CRAFT cyan
        '#9b59b6',   # Nemotron violet
        '#e74c3c',   # Risk magenta
    ]

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(colors=colors),
        textinfo='label+value',
        hovertemplate='%{label}: %{value}<extra></extra>',
    ))

    fig.update_layout(
        title='Blast Radius Composition',
        template='plotly_dark',
        height=400,
        margin=dict(t=60, l=20, r=20, b=20),
    )
    return fig
