"""
ZendureSimulator - A Python Plotly Dash application for simulating Zendure power distribution.
"""

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import pandas as pd
from datetime import datetime, timedelta
from simulator import ZendureSimulator

# Initialize the Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Zendure Power Distribution"
sim = ZendureSimulator()

# Create the layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dcc.Upload(id='upload-data', accept='.log', children=
        html.Div(
            [
                dbc.Button('Zendure Power Distribution Simulator', color="danger", className="me-1", size="lg"),
            ],
            className="d-grid gap-2",
        )),
    ]),
    dbc.Row([
        dbc.Col(dbc.Label("Distribution:", className="m-1"), width="auto"),
        dbc.Col(dcc.Dropdown(['Neutral', 'Max Solar', 'Min Buying'], 'Neutral', id='distribution_mode')),
        dbc.Col(dbc.Label("Start power (W):", className="m-1"), width="auto"),
        dbc.Col(dbc.Input(type="number", min=0, max=250, step=1, value=50, id='start_power'), width="auto"),
        dbc.Col(dbc.Label("Power tolerance (W):", className="m-1"), width="auto"),
        dbc.Col(dbc.Input(type="number", min=0, max=50, step=1, value=10, id='power_tolerance'), width="auto"),
        dbc.Col(dbc.Button("Start", id='start_button', color="primary"), width="auto"),
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
    })
    
], fluid=True, className="p-2")


@app.callback(
    Output('simulation-data', 'data', allow_duplicate=True),
    [Input('upload-data', 'contents')],
    [State('simulation-data', 'data'),
     State('upload-data', 'filename')],
     prevent_initial_call=True
)
def load_logfile(upload_contents, data, filename):
    """Load the log file."""
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return data
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Load the simulation file
    if button_id == 'upload-data':
        return sim.load_logfile(filename, upload_contents)
    
    return data

@app.callback(
    Output('simulation-data', 'data', allow_duplicate=True),
    Input('start_button', 'n_clicks'),
    [State('simulation-data', 'data'),
     State('distribution_mode', 'value'),
     State('start_power', 'value'),
     State('power_tolerance', 'value')],
    prevent_initial_call=True
)
def update_simulation(button, data, distribution_mode, start_power, power_tolerance):
    """Update simulation data based on user actions and time intervals."""
    return sim.do_simulation(data, distribution_mode, start_power, power_tolerance)

@app.callback(
    Output('power-graph', 'figure'),
    [Input('simulation-data', 'data')]
)
def update_power_graph(data):
    """Update the power flow graph."""
    if len(sim.time) == 0:
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
        x=sim.time,
        y=sim.p1,
        mode='lines',
        name='P1',
        line=dict(color='purple', width=2),
    ))
    
    fig.add_trace(go.Scatter(
        x=sim.time,
        y=sim.homeC,
        mode='lines',
        name='Home Consumption',
        line=dict(color='black', width=2),
    ))
    
    fig.add_trace(go.Scatter(
        x=sim.time,
        y=sim.homeZ,
        mode='lines',
        name='Home Zendure',
        line=dict(color='lightgray', width=2),
    ))
    
    fig.add_trace(go.Scatter(
        x=sim.time,
        y=sim.solar,
        mode='lines',
        name='Solar',
        line=dict(color='yellow', width=2),
    ))
    
    fig.add_trace(go.Scatter(
        x=sim.time,
        y=sim.offgrid,
        mode='lines',
        name='Offgrid',
        line=dict(color='red', width=2),
    ))

    if len(sim.sim_p1) > 0:
        fig.add_trace(go.Scatter(
            x=sim.time,
            y=sim.sim_p1,
            mode='lines',
            name='Simulated P1',
            line=dict(color='blue', width=2),
        ))
    
    if len(sim.sim_home) > 0:
        fig.add_trace(go.Scatter(
            x=sim.time,
            y=sim.sim_home,
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
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    fig.update_layout()
    
    return fig

@app.callback(
    Output('charge-graph', 'figure'),
    [Input('simulation-data', 'data')]
)
def update_charge_graph(data):
    """Update the battery charge graph."""
    if len(sim.time) == 0 or len(sim.devices) == 0:
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
    
    # Add charge level trace of all devices
    devices = sim.devices.values()
    for device in devices:
        if len(device.levels) > 0:
            fig.add_trace(go.Scatter(
                x=sim.time,
                y=device.levels,
                mode='lines',
                name=device.name,
                line=dict(color='green', width=2),
                fill='tozeroy',
                fillcolor='rgba(0, 255, 0, 0.1)'
            ))

        if len(device.sim_level) > 0:
            fig.add_trace(go.Scatter(
                x=sim.time,
                y=device.sim_level,
                mode='lines',
                name=f'{device.name} sim',
                line=dict(color='green', width=2),
                fill='tozeroy',
                fillcolor='rgba(0, 255, 0, 0.1)'
            ))
    
    # Add warning zone
    fig.add_hline(y=10, line_dash="dash", line_color="red", opacity=0.1, line_width=0)
    fig.add_hline(y=90, line_dash="dash", line_color="orange", opacity=0.1, line_width=0)
    
    fig.update_layout(
        xaxis_title='Time (seconds)',
        yaxis_title='Charge Level (%)',
        yaxis_range=[0, 100],
        template='plotly_white',
        hovermode='x unified',
        showlegend=True
    )
    
    return fig

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
