import plotly.graph_objects as go
from plotly.subplots import make_subplots

def figure(data, width=None):
    df2=((data.groupby('Publication Year')['PubMed ID']).count()).reset_index()
    df2.columns=['Year','Count']
    df3=((data.groupby('Publication Year')['Citation Count']).sum()).reset_index()
    df3['cumulative']= round(df3['Citation Count'].cumsum(), 0) 
    df3.columns=['Year','citations','Count']
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # Add traces
    fig.add_trace(
        go.Bar(
            x=df2['Year'],
            y=df2['Count'],
            marker=dict(color = '#20425A'),
            hovertemplate =
                '<i>Publications in %{x}</i>: %{y:.0f}<extra></extra>',
            showlegend = False
            
            ), 
        secondary_y=False,
    )

    fig.add_trace(
        go.Line(
            x=df3['Year'],
            y=df3['Count'],
            marker=dict(color = '#f6ac15'),
            hovertemplate =
                '<i>Citations in %{x}</i>: %{y} <extra></extra>',
            ),
        secondary_y='Secondary'
    )

    # Add figure title
    title_size = 17
    if width and width < 370:
        title_size = 12
    fig.update_layout(
        title={
            "text": "<b>OHDSI<br>Publications<br>&<br>Cumulative<br>Citations</b>",
            "pad": {"l": 16, "r": 0, "b": 0, "t": 0},
            "x": 0,
            "xanchor": "left",
            "xref": "paper",
            "y": 0.9,
            "yanchor": "top",
            "yref": "paper",
            "font": {
                "size": title_size,
            },
        },
        showlegend=False,
        margin={"l": 0, "r": 0, "b": 0, "t": 8, "pad": 0},
    )
    # Set x-axis title
    fig.update_xaxes(title_text="Year")
    # Set y-axes titles
    fig.update_yaxes(
        title_text="Number of Publications", 
        secondary_y=False)
    fig.update_yaxes(
        title_text="Number of Citations", 
        secondary_y=True,
    )
    
    fig.update_layout(yaxis={'tickformat': '{:,}'})
    return fig
