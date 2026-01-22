"""
ZendureSimulator - A Python Plotly Dash application for simulating Zendure battery systems.
"""

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import pandas as pd
from datetime import datetime, timedelta

# Initialize the Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Zendure Battery Simulator"

# Initial battery parameters
INITIAL_CAPACITY = 2000  # Wh
INITIAL_CHARGE = 80  # %
INITIAL_POWER = 500  # W

# Create the layout
app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("Zendure Battery Simulator", className="text-center text-primary mb-4"),
            html.P("Simulate and visualize Zendure battery system performance", 
                   className="text-center text-muted mb-4")
        ])
    ]),
    
    # Control Panel
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("Battery Configuration")),
                dbc.CardBody([
                    html.Label("Battery Capacity (Wh):"),
                    dcc.Slider(
                        id='capacity-slider',
                        min=1000,
                        max=5000,
                        step=100,
                        value=INITIAL_CAPACITY,
                        marks={i: str(i) for i in range(1000, 5001, 1000)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    html.Br(),
                    
                    html.Label("Initial Charge Level (%):"),
                    dcc.Slider(
                        id='charge-slider',
                        min=0,
                        max=100,
                        step=5,
                        value=INITIAL_CHARGE,
                        marks={i: f"{i}%" for i in range(0, 101, 20)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    html.Br(),
                    
                    html.Label("Power Draw/Charge (W):"),
                    dcc.Slider(
                        id='power-slider',
                        min=-2000,
                        max=2000,
                        step=50,
                        value=INITIAL_POWER,
                        marks={i: str(i) for i in range(-2000, 2001, 1000)},
                        tooltip={"placement": "bottom", "always_visible": True}
                    ),
                    html.Small("Negative values = charging, Positive values = discharging", 
                              className="text-muted"),
                    html.Br(),
                    html.Br(),
                    
                    dbc.Button("Start Simulation", id="start-button", color="success", className="me-2"),
                    dbc.Button("Reset", id="reset-button", color="secondary"),
                ])
            ])
        ], width=12, lg=4),
        
        # Live Stats Panel
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("Live Statistics")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H5("Current Charge", className="text-muted"),
                            html.H2(id="current-charge", className="text-success"),
                        ]),
                        dbc.Col([
                            html.H5("Remaining Energy", className="text-muted"),
                            html.H2(id="remaining-energy", className="text-info"),
                        ]),
                    ]),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            html.H5("Power Flow", className="text-muted"),
                            html.H2(id="power-flow", className="text-warning"),
                        ]),
                        dbc.Col([
                            html.H5("Runtime/Charge Time", className="text-muted"),
                            html.H2(id="runtime", className="text-primary"),
                        ]),
                    ]),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            html.H5("Status", className="text-muted"),
                            html.H3(id="status", className="text-dark"),
                        ]),
                    ]),
                ])
            ])
        ], width=12, lg=8),
    ], className="mb-4"),
    
    # Graphs
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("Battery Charge Over Time")),
                dbc.CardBody([
                    dcc.Graph(id='charge-graph')
                ])
            ])
        ], width=12, lg=6),
        
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("Power Flow Over Time")),
                dbc.CardBody([
                    dcc.Graph(id='power-graph')
                ])
            ])
        ], width=12, lg=6),
    ], className="mb-4"),
    
    # Data storage and interval
    dcc.Store(id='simulation-data', data={
        'time': [],
        'charge': [],
        'power': [],
        'energy': [],
        'running': False
    }),
    dcc.Interval(id='interval-component', interval=1000, n_intervals=0, disabled=True),
    
], fluid=True, className="p-4")


@app.callback(
    [Output('simulation-data', 'data'),
     Output('interval-component', 'disabled')],
    [Input('start-button', 'n_clicks'),
     Input('reset-button', 'n_clicks'),
     Input('interval-component', 'n_intervals')],
    [State('simulation-data', 'data'),
     State('capacity-slider', 'value'),
     State('charge-slider', 'value'),
     State('power-slider', 'value')]
)
def update_simulation(start_clicks, reset_clicks, n_intervals, data, capacity, charge, power):
    """Update simulation data based on user actions and time intervals."""
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return data, True
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Reset simulation
    if button_id == 'reset-button':
        return {
            'time': [],
            'charge': [],
            'power': [],
            'energy': [],
            'running': False,
            'capacity': capacity,
            'initial_charge': charge,
            'power_draw': power
        }, True
    
    # Start simulation
    if button_id == 'start-button':
        if not data.get('running', False):
            data['running'] = True
            data['capacity'] = capacity
            data['initial_charge'] = charge
            data['power_draw'] = power
            data['time'] = [0]
            data['charge'] = [charge]
            data['power'] = [power]
            data['energy'] = [capacity * charge / 100]
            return data, False
        else:
            data['running'] = False
            return data, True
    
    # Update simulation step
    if button_id == 'interval-component' and data.get('running', False):
        if len(data['time']) == 0:
            return data, True
        
        # Get current values
        current_time = data['time'][-1]
        current_charge = data['charge'][-1]
        current_energy = data['energy'][-1]
        capacity = data.get('capacity', INITIAL_CAPACITY)
        power_draw = data.get('power_draw', INITIAL_POWER)
        
        # Calculate energy change (1 second interval, convert to hours)
        energy_change = -power_draw / 3600  # Wh
        new_energy = current_energy + energy_change
        new_charge = (new_energy / capacity) * 100
        
        # Clamp charge between 0 and 100
        if new_charge <= 0:
            new_charge = 0
            new_energy = 0
            data['running'] = False
        elif new_charge >= 100:
            new_charge = 100
            new_energy = capacity
            data['running'] = False
        
        # Append new data
        data['time'].append(current_time + 1)
        data['charge'].append(new_charge)
        data['power'].append(power_draw)
        data['energy'].append(new_energy)
        
        # Keep only last 300 data points
        if len(data['time']) > 300:
            data['time'] = data['time'][-300:]
            data['charge'] = data['charge'][-300:]
            data['power'] = data['power'][-300:]
            data['energy'] = data['energy'][-300:]
        
        return data, False if data['running'] else True
    
    return data, True


@app.callback(
    [Output('current-charge', 'children'),
     Output('remaining-energy', 'children'),
     Output('power-flow', 'children'),
     Output('runtime', 'children'),
     Output('status', 'children')],
    [Input('simulation-data', 'data')]
)
def update_stats(data):
    """Update the live statistics display."""
    if not data or len(data.get('charge', [])) == 0:
        return "0%", "0 Wh", "0 W", "N/A", "Idle"
    
    current_charge = data['charge'][-1]
    current_energy = data['energy'][-1]
    power = data.get('power_draw', 0)
    capacity = data.get('capacity', INITIAL_CAPACITY)
    
    # Calculate runtime or charge time
    if power > 0:  # Discharging
        if current_energy > 0:
            runtime_hours = current_energy / power
            runtime_str = f"{int(runtime_hours)}h {int((runtime_hours % 1) * 60)}m"
            status = "Discharging"
        else:
            runtime_str = "Empty"
            status = "Empty"
    elif power < 0:  # Charging
        remaining_capacity = capacity - current_energy
        if remaining_capacity > 0:
            charge_time_hours = remaining_capacity / abs(power)
            runtime_str = f"{int(charge_time_hours)}h {int((charge_time_hours % 1) * 60)}m"
            status = "Charging"
        else:
            runtime_str = "Full"
            status = "Full"
    else:
        runtime_str = "Idle"
        status = "Idle"
    
    charge_str = f"{current_charge:.1f}%"
    energy_str = f"{current_energy:.0f} Wh"
    power_str = f"{power} W"
    
    return charge_str, energy_str, power_str, runtime_str, status


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
        fig.add_trace(go.Scatter(x=[], y=[], mode='lines', name='Power Flow'))
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
        y=data['power'],
        mode='lines',
        name='Power Flow',
        line=dict(color='purple', width=2),
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


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
