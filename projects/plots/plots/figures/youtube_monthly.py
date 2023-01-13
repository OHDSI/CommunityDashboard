import plotly.graph_objects as go

def figure(df2, width=None):
    bar_fig2=go.Figure()
    bar_fig2.add_trace(
        go.Bar(
            x=df2['Date'],
            y=df2['Count'],
            marker=dict(color = '#20425A'),
            showlegend=False
        )
    )
    bar_fig2.update_layout(
        title={
        'text': "<b>Hours Viewed for each month</b>",
        'y':0.9,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'})
    bar_fig2.update_xaxes(type='category')
    return bar_fig2