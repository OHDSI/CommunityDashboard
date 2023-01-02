import plotly.graph_objects as go
from plotly.subplots import make_subplots

def figure(data, width=None):
    currentAuthorSummaryTable = data
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # Add traces
    fig.add_trace(
        go.Bar(
            x=currentAuthorSummaryTable['Year'],
            y=currentAuthorSummaryTable['All New Authors'],
            marker=dict(color = '#20425A'),
            hovertemplate =
                '<i>New Authors in %{x}</i>: %{y:.0f}<extra></extra>',
            showlegend = False
            
            ), 
        secondary_y=False,
    )

    fig.add_trace(
        go.Line(
            x=currentAuthorSummaryTable['Year'],
            y=currentAuthorSummaryTable['Total Authors'],
            marker=dict(color = '#f6ac15'),
            hovertemplate =
                '<i>Cumulative Authors by %{x}</i>: %{y} <extra></extra>',
            ),
        secondary_y='Secondary'
    )

    # Add figure title
    fig.update_layout(title_text="<b>New & Cumulative OHDSI Researchers</b>", title_x=0.5, showlegend=False)
    # Set x-axis title
    fig.update_xaxes(title_text="Year")
    # Set y-axes titles
    fig.update_yaxes(
        title_text="Number of New Authors", 
        secondary_y=False)
    fig.update_yaxes(
        title_text="Number of Cumulative Authors", 
        secondary_y=True)
    fig.update_layout(yaxis={'tickformat': '{:,}'})
    return fig
