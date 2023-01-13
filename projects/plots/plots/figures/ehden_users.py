import plotly.graph_objects as go

def figure(data, width=None):
    df = data
    bar_fig1=go.Figure()
    bar_fig1.add_trace(
        go.Bar(
            x=df.year,
            y=df.number_of_users,
            marker=dict(color = '#20425A'),
            showlegend=False
        )
    )
    
    title_size = 17
    if width and width < 370:
        title_size = 12
    bar_fig1.update_layout(
        title={
            "text": "<b>Users<br>by<br>Year</b>",
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
        margin={"l": 0, "r": 0, "b": 0, "t": 8, "pad": 0},
    )
    bar_fig1.update_xaxes(type='category')
    
    return bar_fig1