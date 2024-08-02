import dash
import os
from dash import dcc, html, Input, Output, State
import pandas as pd
import plotly.graph_objects as go
import io
import numpy as np
import plotly.io as pio
from sqlalchemy import create_engine 
from dotenv import load_dotenv  # Add this line

# Load environment variables from .env file
load_dotenv() 
db_url =  create_engine(f'{os.getenv("ENGINE")}://{os.getenv("DTABASE_USER")}:{os.getenv("PASSWORD")}@{os.getenv("HOST")}/{os.getenv("CPI_DATABASE")}')

# Construct database URL from environment variables
#print("DB URL : ", db_url)


query = '''
with t1 as(
    select A.series as series, A.year as year, A.month as month_number, F.description as month, 
    B.description as state, C.description as sector, D.description as grp, 
    E.description as subgroup, A.index as index, A.inflation as inflation, A.base_year as base_year
    from cpi_fact as A 
    JOIN state as B on A.state_code = B.state_code 
    JOIN sector as C on A.sector_code = C.sector_code 
    JOIN groups as D on A.group_code = D.group_code 
    JOIN subgroups as E on A.subgroup_code = E.subgroup_code 
    JOIN month as F on A.month = F.month 
    order by year, month_number, state, sector, grp, subgroup
)
SELECT year, month, month_number, state, sector, grp, subgroup, base_year,
 inflation, index, concat(year, month_number) as year_month,
 concat(year, month) as xaxislabel 
FROM t1 where subgroup is NULL or subgroup like '' and series = 'Current';
'''

# Fetch the data
raw_data = pd.read_sql_query(query, db_url)
cpi_data = pd.DataFrame(raw_data)
cpi_data['month_number'] = cpi_data['month_number'].astype(str).str.zfill(2)
cpi_data['year_month'] = cpi_data['year'].astype(str) + cpi_data['month_number'].astype(str)
cpi_data = cpi_data.sort_values(by=['year_month'])
cpi_data['year_month2'] = cpi_data['year_month'].str[:4] + '-' + cpi_data['year_month'].str[4:]
cpi_data['year_month2'] = cpi_data['year_month2'].astype(str)
cpi_data['xaxislabel'] = cpi_data['xaxislabel'].str[:4] + '-' + cpi_data['xaxislabel'].str[4:7]

# Get unique years for dropdown
available_years = ['All'] + [str(year) for year in np.sort(cpi_data['year'].unique())]

# Create a Dash application
external_stylesheets = [
    {
        "href": "https://fonts.googleapis.com/css2?family=Lato:wght@400;700&display=swap",
        "rel": "stylesheet",
    },
    {
        "href": "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css",
        "rel": "stylesheet",
    },
]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, routes_pathname_prefix = '/viz/cpi/', requests_pathname_prefix = '/viz/cpi/')
# app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "Consumer Price Index"

# Define default dropdown values function
def get_default_dropdown_values():
    default_state = 'All India'
    default_sector = 'Combined'
    default_group = 'General'
    default_plot_type = 'Index'
    return default_state, default_sector, default_group, default_plot_type

# Get default dropdown values
default_state, default_sector, default_group, default_plot_type = get_default_dropdown_values()

# App layout
app.layout = html.Div(
    className="content-wrapper",
    children=[
        # Sidebar
        html.Div(
            style={'flex': '0 1 320px', 'padding': '10px', 'boxSizing': 'border-box'},
            children=[
                html.H1(
                    html.Div(
                        "Select Parameters to Get Chart",
                        className="parameter-data",
                        style={'fontSize': '15px', 'fontWeight': 'normal'},
                    ),
                    style={'marginBottom': '25px', 'marginTop': '20px'}
                ),
                html.Div(
                    children=[
                        html.Label("State:", className="menu-title"),
                        dcc.Dropdown(
                            id='state-dropdown',
                            options=[{'label': state, 'value': state} for state in np.unique(cpi_data['state'])],
                            value=default_state,  # Default value
                            className="dropdown",
                            searchable= False,
                            clearable=False,
                        )
                    ],
                    style={'marginBottom': '20px'}
                ),
                html.Div(
                    children=[
                        html.Label("Base Year", className="menu-title"),
                        dcc.Dropdown(
                            id='base-year-dropdown',
                            options=[{'label': base, 'value': base} for base in np.unique(cpi_data['base_year'])],
                            value='2012',  # Default value
                            className="dropdown",
                            searchable= False,
                            clearable=False,
                        )
                    ],
                    style={'marginBottom': '20px'}
                ),
                html.Div(
                    children=[
                        html.Label("Sector:", className="menu-title"),
                        dcc.Dropdown(
                            id='sector-dropdown',
                            className="dropdown",
                            value=default_sector,  # Default value
                            multi=False,  # Ensure only one option can be selected
                            searchable= False,
                            clearable=False,
                        )
                    ],
                    style={'marginBottom': '20px'}
                ),
                html.Div(
                    children=[
                        html.Label("Group:", className="menu-title"),
                        dcc.Dropdown(
                            id='group-dropdown',
                            className="dropdown",
                            value=default_group,
                            searchable= False,
                            clearable=False,
                        )
                    ],
                    style={'marginBottom': '20px'}
                ),
                html.Div(
                    children=[
                        html.Label("Indicator:", className="menu-title"),
                        dcc.Dropdown(
                            id='plot-type-dropdown',
                            options=[
                                {'label': 'Index', 'value': 'Index'},
                                {'label': 'Inflation', 'value': 'Inflation'}
                            ],
                            value=default_plot_type,  # Default value
                            className="dropdown",
                            searchable= False,
                            clearable=False,
                        )
                    ],
                    style={'marginBottom': '0px'}
                ),
                html.Div(
                    children=[
                        html.Div(children="Year", className="menu-title"),
                        dcc.Dropdown(
                            id="year-dropdown",
                            options=[
                                {'label': 'Select All', 'value': 'Select All'}
                            ] + [{'label': year, 'value': year} for year in cpi_data['year'].unique()],
                            multi=True,
                            placeholder="Select Year",
                            className="dropdown",
                            value=  "Select All",  # Select all by default
                        ),
                    ],
                    style={'marginBottom': '0px'}
                ),
                html.Button(
                    'Apply', id='plot-button', n_clicks=0, className='mr-1',
                    style={
                        'width': '100%',
                        'background': 'radial-gradient(circle, #0a266c 0, #085858 3%, #0a266c 94%)',
                        'color': 'white',
                        'border': 'none',
                        'padding': '10px 20px',
                        'text-align': 'center',
                        'text-decoration': 'none',
                        'display': 'inline-block',
                        'font-size': '16px',
                        'margin': '20px 0',
                        'cursor': 'pointer',
                        'border-radius': '8px',
                        'marginTop': '30px',
                        'marginBottom': '0px'
                    }
                ),
                # html.Div(
                #     id='info-text',
                #     style={'display': 'none', 'position': 'absolute', 'bottom': '40px', 'right': '10px', 'background-color': 'white', 'padding': '10px', 'border-radius': '5px', 'box-shadow': '0px 0px 5px 0px rgba(0,0,0,0.75)'},
                #     children=[
                #         html.P("This is a CPI Time Series Plot visualization. Select the parameters from the dropdowns on the left to generate the plot."),
                #     ]
                # ),
                # html.Button(
                #     html.I(className="fas fa-info-circle"),
                #     id="info-button",
                #     className='info-button',
                #     style={
                #         'position': 'absolute',
                #         'bottom': '10px',
                #         'right': '10px',
                #         'background': 'none',
                #         'border': 'none',
                #         'color': 'black',
                #         'cursor': 'pointer',
                #         'font-size': '24px'
                #     }
                # ),
                html.Button(
                    'Download', id='download-button', n_clicks=0, className='mr-1',
                    style={
                        'width': '100%',
                        'background': 'radial-gradient(circle, #0a266c 0, #085858 3%, #0a266c 94%)',
                        'color': 'white',
                        'border': 'none',
                        'padding': '10px 20px',
                        'text-align': 'center',
                        'text-decoration': 'none',
                        'display': 'inline-block',
                        'font-size': '16px',
                        'margin': '20px 0',
                        'cursor': 'pointer',
                        'border-radius': '8px',
                        'marginBottom': '10px'
                    }
                ),
            ]
        ),
        # Graph area
        html.Div(
            style={'flex': '1', 'padding': '20px', 'position': 'right',  'margin-right': '10px'},
            children=[
                dcc.Loading(
                    id="loading-graph",
                    type="circle",
                    color='#83b944',  # or "default"
                    children=[
                        html.Div(
                            id='graph-container',
                            # style={'width': '100%', 'height': '800px'},
                            children=[
                                html.Div(
                                    className="loader",  # add a class for styling
                                    id="loading-circle",
                                    style={"position": "absolute", "top": "50%", "left": "50%", "transform": "translate(-50%, -50%)"}
                                ),
                                dcc.Graph(id='plot-output', config={"displayModeBar": False})  # Placeholder for the graph
                            ]
                        ),
                    ]
                ),
            ]
        ),
        dcc.Download(id="download")
    ]
)
@app.callback(
    Output('year-dropdown', 'options'),
    [Input('base-year-dropdown', 'value')]
)
def update_year_dropdown(selected_base_year):
    if selected_base_year:
        filtered_years = cpi_data[cpi_data['base_year'] == selected_base_year]['year'].unique()
        return [{'label': 'Select All', 'value': 'Select All'}]+ [{'label': year, 'value': year} for year in sorted(filtered_years)]
    else:
        return [{'label': 'Select All', 'value': 'Select All'}] + [{'label': year, 'value': year} for year in sorted(cpi_data['year'].unique())]


# Define callback to update sector dropdown based on state selection
@app.callback(
    Output('sector-dropdown', 'options'),
    [Input('state-dropdown', 'value')]
)
def update_sector_dropdown(selected_state):
    filtered_df = cpi_data[cpi_data['state'] == selected_state]
    sectors = filtered_df['sector'].unique()
    return [{'label': sector, 'value': sector} for sector in sectors]

# Define callback to update group dropdown based on sector selection
@app.callback(
    Output('group-dropdown', 'options'),
    [Input('sector-dropdown', 'value')]
)
def update_group_dropdown(selected_sector):
    filtered_df = cpi_data.copy()
    if selected_sector is not None:
        filtered_df = filtered_df[filtered_df['sector'] == selected_sector]
    groups = filtered_df['grp'].unique()
    return [{'label': group, 'value': group} for group in groups]


# Define callback to update graph based on dropdown inputs
@app.callback(
    Output('plot-output', 'figure'),
    [Input('plot-button', 'n_clicks')],
    [State('state-dropdown', 'value'),
     State('sector-dropdown', 'value'),
     State('group-dropdown', 'value'),
     State('plot-type-dropdown', 'value'),
     State('year-dropdown', 'value'),
     State('base-year-dropdown', 'value')]
)
def update_plot(n_clicks, state, sector, group, plot_type, selected_years,base):
    if n_clicks > 0 or (state, sector, group, plot_type) == get_default_dropdown_values():
        filtered_df = cpi_data.copy()
        if 'Select All' in selected_years:
            selected_years = cpi_data['year'].unique()
        else:
            selected_years = [year for year in selected_years if year != 'Select All']

        filtered_df = cpi_data[(cpi_data['year'].isin(selected_years))]
        filtered_df = filtered_df[filtered_df['state'] == state]
        filtered_df = filtered_df[(filtered_df['sector'] == sector) & (filtered_df['grp'] == group)&(filtered_df['base_year'] == base)]
        filtered_df = filtered_df.sort_values('year_month2')
        # print(filtered_df)

        fig = go.Figure()

        if plot_type == 'Index':
            fig.add_trace(go.Scatter(x=filtered_df['year_month2'], y=filtered_df['index'], mode='lines+markers', name='Index', line=dict(color='#0F4366'), yaxis='y', hovertemplate='%{x}, Index %{y:.2f}<extra></extra>'))
            #string = "Consumer Price Index"
            fig.update_layout(
                # title={
                #     'text': f"<span style='text-decoration:underline;'>{string}</span>",
                #     'x': 0.5,
                #     'xanchor': 'center'
                # },
                xaxis_title='Year',
                yaxis_title= "Index",
                template='plotly_white',
                title_font=dict(size=25, family='Arial, sans-serif', color='black', weight='bold'),
                xaxis_title_font=dict(size=18, family='Arial, sans-serif', color='black', weight='bold'),
                yaxis_title_font=dict(size=18, family='Arial, sans-serif', color='black', weight='bold'),
                font_color='black',
                yaxis=dict(title="<b>Index</b>", side='left', color='black',showgrid= True),
                xaxis=dict(showgrid=True, gridcolor='lightgray', tickangle=270),
                margin = dict(t = 0),
                # height=800,
                # width=1520,
                title_x=0.5,
            )
        else:
            fig.add_trace(go.Scatter(x=filtered_df['year_month2'], y=filtered_df['inflation'], mode='lines+markers', name='Inflation', line=dict(color='#EF553B'), yaxis='y', hovertemplate='%{x}, Inflation: %{y:.2f}%<extra></extra>'))
            #string = "Consumer Price Index"
            fig.update_layout(
                # title={
                #     'text': f"<span style='text-decoration:underline;'>{string}</span>",
                #     'x': 0.5,
                #     'xanchor': 'center'
                # },
                xaxis_title='Year',
                yaxis_title= "Inflation (in %)",
                template='plotly_white',
                title_font=dict(size=25, family='Arial, sans-serif', color='black', weight='bold'),
                xaxis_title_font=dict(size=18, family='Arial, sans-serif', color='black', weight='bold'),
                yaxis_title_font=dict(size=18, family='Arial, sans-serif', color='black', weight='bold'),
                font_color='black',
                yaxis=dict(title="<b>Inflation</b>", side='left', color='black',showgrid= True),
                xaxis=dict(showgrid=True, gridcolor='lightgray', tickangle=270),
                margin = dict(t = 0),
                # height=800,
                # width=1520,
                title_x=0.5,
            )
        return fig

    else:
        return go.Figure()

# Define callback for downloading SVG
@app.callback(
    Output("download", "data"),
    [Input('download-button', 'n_clicks')],
    [State('state-dropdown', 'value'),
     State('sector-dropdown', 'value'),
     State('group-dropdown', 'value'),
     State('plot-type-dropdown', 'value'),
     State('year-dropdown', 'value'),
     State('base-year-dropdown', 'value')
     ]
)
def download_plot(download_clicks, state, sector, group, plot_type, selected_years,base):
    ctx = dash.callback_context
    if not ctx.triggered:
        return None
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'download-button':
            filtered_df = cpi_data.copy()
            if 'Select All' in selected_years:
                selected_years = cpi_data['year'].unique()
            else:
                selected_years = [year for year in selected_years if year != 'Select All']

            filtered_df = filtered_df[filtered_df['state'] == state]
            filtered_df = filtered_df[(filtered_df['sector'] == sector) & (filtered_df['grp'] == group)&(filtered_df['base_year'] == base)]
            filtered_df = filtered_df.sort_values('year_month2')

            fig = go.Figure()
            if plot_type == 'Index':
                fig.add_trace(go.Scatter(x=filtered_df['year_month2'], y=filtered_df['index'], mode='lines+markers', name='Index', line=dict(color='#0F4366'), yaxis='y', hovertemplate='%{x}, Index %{y:.2f}<extra></extra>'))
                #string = "Consumer Price Index"
                fig.update_layout(
                    # title={
                    #     'text': f"<span style='text-decoration:underline;'>{string}</span>",
                    #     'x': 0.5,
                    #     'xanchor': 'center'
                    # },
                    xaxis_title='Year',
                    yaxis_title= "Index",
                    template='plotly_white',
                    title_font=dict(size=25, family='Arial, sans-serif', color='black', weight='bold'),
                    xaxis_title_font=dict(size=18, family='Arial, sans-serif', color='black', weight='bold'),
                    yaxis_title_font=dict(size=18, family='Arial, sans-serif', color='black', weight='bold'),
                    font_color='black',
                    yaxis=dict(title="<b>Index</b>", side='left', color='black',showgrid= True),
                    xaxis=dict(showgrid=True, gridcolor='lightgray', tickangle=270),
                    margin = dict(t = 0),
                    # height=800,
                    # width=1520,
                    title_x=0.5,
                )
            elif plot_type == 'Inflation':
                fig.add_trace(go.Scatter(x=filtered_df['year_month2'], y=filtered_df['inflation'], mode='lines+markers', name='Inflation', line=dict(color='#EF553B'), yaxis='y', hovertemplate='%{x}, Inflation: %{y:.2f}%<extra></extra>'))
                #string = "Consumer Price Index"
                fig.update_layout(
                    # title={
                    #     'text': f"<span style='text-decoration:underline;'>{string}</span>",
                    #     'x': 0.5,
                    #     'xanchor': 'center'
                    # },
                    xaxis_title='Year',
                    yaxis_title= "Inflation (in %)",
                    template='plotly_white',
                    title_font=dict(size=25, family='Arial, sans-serif', color='black', weight='bold'),
                    xaxis_title_font=dict(size=18, family='Arial, sans-serif', color='black', weight='bold'),
                    yaxis_title_font=dict(size=18, family='Arial, sans-serif', color='black', weight='bold'),
                    font_color='black',
                    yaxis=dict(title="<b>Inflation</b>", side='left', color='black',showgrid= True),
                    xaxis=dict(showgrid=True, gridcolor='lightgray', tickangle=270),
                    margin = dict(t = 0),
                    # height=800,
                    # width=1520,
                    title_x=0.5,
                )
            # Generate a unique filename for each download
            #filename = f"plot_{state}_{sector}_{group}_{plot_type}.svg"
            #fig.write_image(filename, format='svg')
            # Return the filename as data
            #return dcc.send_file(filename)
            svg_str = pio.to_image(fig, format="svg")

        # Create a BytesIO buffer and write the SVG string to it
            buffer = io.BytesIO()
            buffer.write(svg_str)
            buffer.seek(0)
            return dcc.send_bytes(buffer.getvalue(), "plot.svg")
        else:
            return None
        
# @app.callback(
#     Output('info-text', 'style'),
#     Input('info-button', 'n_clicks'),
#     State('info-text', 'style'),
#     prevent_initial_call=True
# )
# def toggle_info_text(n_clicks, style):
#     if n_clicks is None:
#         return style
#     if style['display'] == 'none':
#         style['display'] = 'block'
#         style['zIndex'] = 999  # Ensure info text is above other elements
#     else:
#         style['display'] = 'none'
#     return style

# Define callback to show info dialog
# Define callback to show info message
#@app.callback(
   # Output('info-text', 'style'),
    #Input('info-button', 'n_clicks'),
    #State('info-text', 'style'),
    #prevent_initial_call=True
#)
#def toggle_info_text(n_clicks, style):
    #if n_clicks is None:
        #return style
    #if style['display'] == 'none':
        #style['display'] = 'block'
    #else:
        #style['display'] = 'none'
    #return style



if __name__ == '__main__':
    app.run_server(debug=True,dev_tools_ui=False,dev_tools_props_check=False,port=9001,host='0.0.0.0')