from plotly.subplots import make_subplots
import plotly.graph_objects as go
import numpy as np

def figure(data, width=None):
    df=data[data.channelTitle.str.startswith('OHDSI')].copy(deep=True)
    # print(df['Length'])
    df['Duration'] = df.apply(lambda x: int(x['Length'][0:2]) * 3600 + \
                                int(x['Length'][3:5]) * 60 + \
                                    int(x['Length'][6:8]), axis = 1)

    # fig = make_subplots(rows=1, cols=2,
    #                     subplot_titles=("Youtube Hours Created","Cumulative Hrs Watched"))
    df4=df.groupby('yr').Duration.sum().reset_index()
    df4.columns=['Year','SumSeconds']
    # df4['Hrs Created']=df4['SumSeconds'].dt.days*24 + df4['SumSeconds'].dt.seconds/3600
    df4['Hrs Created']=df4['SumSeconds']/3600
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add traces
    fig.add_trace(
        go.Bar(
            x=df4['Year'],
            y=df4['Hrs Created'],
            marker=dict(color = '#20425A'),
            hovertemplate =
                '<i>%{x}</i>: %{y:.0f} hours of content created <extra></extra>',
            showlegend = False
            
            ), 
        secondary_y=False,
    )
    # df['hrsWatched']=(df.Duration.dt.days*24+df.Duration.dt.seconds/3600)*df['Total Views']
    df4=df.groupby('yr').hrsWatched.sum().reset_index()
    df4.columns=['Year','HrsWatched']
    df4['Cumulative Hrs Watched']= np.round(df4['HrsWatched'].cumsum(), 0)
    # df4['Cumulative Hrs Watched'] = df4['Cumulative Hrs Watched'].apply(lambda x :int(x))
    # df4['Cumulative Hrs Watched'] = df4['Cumulative Hrs Watched'].apply(lambda x : "{:,}".format(x))
    fig.add_trace(
        go.Line(
            x=df4['Year'],
            y=df4['Cumulative Hrs Watched'],
            marker=dict(color = '#f6ac15'),
            hovertemplate =
                '<i>%{x}</i>: %{y} hours of video watched <extra></extra>'

            ),
            
        secondary_y='Secondary'
    )
    # Add figure title
    title_size = 17
    if width and width < 370:
        title_size = 12
    fig.update_layout(
        title={
            "text": "<b>YouTube<br>Annually</b>",
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
        showlegend=False)
    # Set x-axis title
    fig.update_xaxes(title_text="Year")
    # Set y-axes titles
    fig.update_yaxes(
        title_text="Content Hours Created", 
        secondary_y=False)
    fig.update_yaxes(
        title_text="Cumulative Hours Watched", 
        secondary_y=True)
    
    return fig