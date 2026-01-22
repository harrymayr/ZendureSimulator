"""
ZendureSimulator - A Python Plotly Dash application for simulating Zendure power distribution.
"""

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import pandas as pd
from datetime import datetime, timedelta
import simulator

# Initialize the Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Zendure Power Distribution"

# Initial battery parameters
INITIAL_CAPACITY = 2000  # Wh
INITIAL_CHARGE = 80  # %
INITIAL_POWER = 500  # W

# Create the layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dcc.Upload(id='upload-data', accept='.csv,.log', children=
        html.Div(
            [
                dbc.Button('Zendure Power Distribution Simulator', color="danger", className="me-1", size="lg"),
            ],
            className="d-grid gap-2",
        ))
    ]),
    
    # Graphs
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("Power Flow Over Time")),
                dbc.CardBody([
                    dcc.Graph(id='power-graph')
                ])
            ])
        ]),
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("Battery Charge Over Time")),
                dbc.CardBody([
                    dcc.Graph(id='charge-graph')
                ])
            ])
        ])
    ]),
    
    # Data storage and interval
    dcc.Store(id='simulation-data', data={
        'time': [],
        'charge': [],
        'p1': [],
        'home': [],
        'solar': [],
        'simp1': [],
        'simhome': []
    })
    # dcc.Interval(id='interval-component', interval=1000, n_intervals=0, disabled=True),
    
], fluid=True, className="p-4")


@app.callback(
    Output('simulation-data', 'data'),
    [Input('upload-data', 'contents')],
    [State('simulation-data', 'data'),
     State('upload-data', 'filename'),]
)
def update_simulation(upload_contents, data, filename):
    """Update simulation data based on user actions and time intervals."""
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return data
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Load the simulation file
    if button_id == 'upload-data':
        return simulator.load_logfile(filename, upload_contents)
    
    return data

@app.callback(
    Output('charge-graph', 'figure'),
    [Input('simulation-data', 'data')]
)
def update_charge_graph(data):
    """Update the battery charge graph."""
    if not data or len(data.get('time', [])) == 0:
        # Empty graph
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[], y=[], mode='lines', name='Charge Level'))
        fig.update_layout(
            xaxis_title='Time (seconds)',
            yaxis_title='Charge Level (%)',
            yaxis_range=[0, 100],
            template='plotly_white',
            hovermode='x unified'
        )
        return fig
    
    fig = go.Figure()
    
    # Add charge level trace
    fig.add_trace(go.Scatter(
        x=data['time'],
        y=data['charge'],
        mode='lines',
        name='Charge Level',
        line=dict(color='green', width=2),
        fill='tozeroy',
        fillcolor='rgba(0, 255, 0, 0.1)'
    ))
    
    # Add warning zone
    fig.add_hrect(y0=0, y1=20, fillcolor="red", opacity=0.1, line_width=0)
    fig.add_hrect(y0=20, y1=40, fillcolor="orange", opacity=0.1, line_width=0)
    
    fig.update_layout(
        xaxis_title='Time (seconds)',
        yaxis_title='Charge Level (%)',
        yaxis_range=[0, 100],
        template='plotly_white',
        hovermode='x unified',
        showlegend=True
    )
    
    return fig


@app.callback(
    Output('power-graph', 'figure'),
    [Input('simulation-data', 'data')]
)
def update_power_graph(data):
    """Update the power flow graph."""
    if not data or len(data.get('time', [])) == 0:
        # Empty graph
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[], y=[], mode='lines', name='P1'))
        fig.update_layout(
            xaxis_title='Time (seconds)',
            yaxis_title='Power (W)',
            template='plotly_white',
            hovermode='x unified'
        )
        return fig
    
    fig = go.Figure()
    
    # Add power flow trace
    fig.add_trace(go.Scatter(
        x=data['time'],
        y=data['p1'],
        mode='lines',
        name='P1',
        line=dict(color='purple', width=2),
    ))
    
    fig.add_trace(go.Scatter(
        x=data['time'],
        y=data['home'],
        mode='lines',
        name='Home',
        line=dict(color='lightgray', width=2),
    ))
    
    fig.add_trace(go.Scatter(
        x=data['time'],
        y=data['solar'],
        mode='lines',
        name='Solar',
        line=dict(color='yellow', width=2),
    ))
    
    fig.add_trace(go.Scatter(
        x=data['time'],
        y=data['simp1'],
        mode='lines',
        name='Simulated P1',
        line=dict(color='blue', width=2),
    ))
    
    fig.add_trace(go.Scatter(
        x=data['time'],
        y=data['simhome'],
        mode='lines',
        name='Simulated Home',
        line=dict(color='brown', width=2),
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    
    fig.update_layout(
        xaxis_title='Time (seconds)',
        yaxis_title='Power (W)',
        template='plotly_white',
        hovermode='x unified',
        showlegend=True
    )
    
    return fig

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
