import plotly.graph_objects as go

def figure(data, width=None):
    df = data
    bar_fig2=go.Figure()
    bar_fig2.add_trace(
        go.Bar(
            x=df.year,
            y=df.completions,
            marker=dict(color = '#20425A'),
            showlegend=False
        )
    )
    bar_fig2.update_layout(
        title={
        'text': "Course Completions by Year",
        'y':0.9,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'})
    bar_fig2.update_xaxes(type='category')
    bar_fig2.update_yaxes(range=[0,1500])
    return bar_fig2