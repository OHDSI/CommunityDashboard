import dash
import ast
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from . import key_vault, pubmed_miner
import plotly.express as px
import pandas as pd 

def convert_time(time_str):
    """Takes time values from Youtube duration
        '8M12S' or '3H10M5S' 
    """
    import datetime,time
    #Strip PT from string (Period Time)
    time_str=time_str[2:]
    filter=''
    filter_list=['H','M','S']
    for filter_item in filter_list:
        if filter_item in time_str:
            filter+='%'+filter_item*2
    ntime=time.strptime(time_str,filter)
    return datetime.timedelta(hours=ntime.tm_hour,minutes=ntime.tm_min,seconds=ntime.tm_sec)


def build_education_dash():
    container_name='youtube'
    key_dict = key_vault.get_key_dict()
    container=pubmed_miner.init_cosmos(key_dict, container_name)
    query = "SELECT * FROM c"
    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))
    videos=[]
    for item in items:
        #Review the log of counts and find the last two and subtract them for recent views
        df=pd.DataFrame(item['counts']).sort_values('checkedOn',ascending=False).reset_index()
        total_views=int(df.viewCount[0])
        if len(df)==1:
            recent_views=int(df.viewCount[0])
        else:
            recent_views=int(df.viewCount[0])-int(df.viewCount[1])
        videos.append({'id':item['id'],
                    'Title':item['title'],
                    # 'Duration':convert_time(item['duration']),
                    'Duration':item['duration'],
                    'Date Published':pd.to_datetime(item['publishedAt']),
                    'Total Views':total_views,
                    'Recent Views':recent_views,
                    'channelTitle':item['channelTitle']}
                    )
    df=pd.DataFrame(videos)
    import plotly.express as px
    df=df[df.channelTitle.str.startswith('OHDSI')].copy(deep=True)
    # df['Duration'] = df.apply(lambda x: str(x['Duration'])[2:], axis = 1)
    df['Duration'] = df.apply(lambda x: convert_time(x['Duration']), axis = 1)
    print(df['Duration'])
    df['yr']=df['Date Published'].dt.year
    

    from plotly.subplots import make_subplots
    import plotly.graph_objects as go
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("Youtube Hours Created","Cumulative Hrs Watched"))
    df4=df.groupby('yr').Duration.sum().reset_index()
    df4.columns=['Year','SumSeconds']
    df4['Hrs Created']=df4['SumSeconds'].dt.days*24+df4['SumSeconds'].dt.seconds/3600
    fig.add_trace(
        go.Bar(
        x=df4['Year'],
        y=df4['Hrs Created']),
        row=1, col=1
        )
    df['hrsWatched']=(df.Duration.dt.days*24+df.Duration.dt.seconds/3600)*df['Total Views']
    df4=df.groupby('yr').hrsWatched.sum().reset_index()
    df4.columns=['Year','HrsWatched']
    df4['Cumulative Hrs Watched']=df4['HrsWatched'].cumsum()
    fig.add_trace(
        go.Line(
        x=df4['Year'],
        y=df4['Cumulative Hrs Watched']),
        row=1, col=2
        )
    df['Date Published']=df['Date Published'].dt.strftime('%Y-%m-%d')
    df['Title']=df.apply(lambda row:"[{}](https://www.youtube.com/watch?v={})".format(row.Title,row.id),axis=1)
    df['Length'] = df.apply(lambda x: str(x['Duration'])[7:], axis = 1)

    fig.update_layout( title_text="Youtube Video Analysis", showlegend=False)
    cols=['Title','Date Published','Length','Total Views','Recent Views']
    layout=html.Div([
                dcc.Interval(
                    id='interval-component',
                    interval=1*1000 # in milliseconds
                ),
                html.Div(
                    children=[
                    html.Br(),
                    html.Br(),
                    html.Br(),
                    html.H1("YouTube Analysis", 
                        style={
                            'font-family': 'Saira Extra Condensed',
                            'color': '#20425A',
                            'fontWeight': 'bold',
                            'text-align': 'center'

                        }
                    ),
                    
                    html.Div(children=
                    [
                        dbc.Row(
                            [
                                dbc.Col(html.Div(id='bar-container'), width = 6),
                                dbc.Col(html.Div(id='line-container'), width = 6)
                            ]
                        )
                    ]),

                    # dcc.Graph(id='videos',figure=fig), 
                    html.Div(),
                    dash_table.DataTable(
                        id = 'datatable-interactivity',
                        data = df.sort_values('Date Published',ascending=False).to_dict('records'), 
                        columns = [{"name": i, "id": i,'presentation':'markdown'} for i in cols],
                        style_cell={
                            'height': 'auto',
                            # all three widths are needed
                            'minWidth': '10px', 'width': '10px', 'maxWidth': '250px',
                            'whiteSpace': 'normal',
                            'textAlign': 'left'
                        },
                        sort_action='native',
                        
                        page_current=0,
                        page_size=20,
                        page_action='native',
                        filter_action='native',

                        sort_mode="single",         # sort across 'multi' or 'single' columns
                        column_selectable="multi",  # allow users to select 'multi' or 'single' columns
                        selected_columns=[],        # ids of columns that user selects
                        selected_rows=[],           # indices of rows that user selects

                        style_data={
                            'color': 'black',
                            'backgroundColor': 'white',
                            'font-family': 'Saira Extra Condensed'
                        },
                        style_filter=[
                            {
                                'color': 'black',
                                'backgroundColor': '#20425A',
                                'font-family': 'Saira Extra Condensed'
                            }
                        ],
                        style_header={
                            'font-family': 'Saira Extra Condensed',
                            'background-color': '#20425A',
                            'color': 'white',
                            'fontWeight': 'bold'
                        }
                    )
                            
                    ]
                )
            ])
    return layout