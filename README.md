# ZendureSimulator

A Python Plotly Dash application for simulating Zendure battery systems. This interactive web application allows you to visualize and analyze battery performance under different configurations and load conditions.

## Features

- **Interactive Dashboard**: Real-time visualization of battery performance
- **Customizable Parameters**: Adjust battery capacity, charge level, and power draw
- **Live Statistics**: Monitor current charge, remaining energy, power flow, and runtime
- **Dynamic Graphs**: Visualize battery charge and power flow over time
- **Realistic Simulation**: Accurate battery discharge/charge calculations

## Requirements

- Python 3.8 or higher
- Dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:
```bash
git clone https://github.com/FireSon/ZendureSimulator.git
cd ZendureSimulator
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:8050
```

3. Use the interactive controls to:
   - Set the battery capacity (1000-5000 Wh)
   - Set the initial charge level (0-100%)
   - Set the power draw/charge rate (-2000 to 2000 W)
     - Negative values simulate charging
     - Positive values simulate discharging
   - Click "Start Simulation" to begin
   - Click "Reset" to clear the simulation data

## Application Components

### Battery Configuration Panel
- **Battery Capacity**: Total energy storage capacity in Watt-hours (Wh)
- **Initial Charge Level**: Starting battery charge percentage
- **Power Draw/Charge**: Power flow in Watts (W)
  - Positive: Discharging (battery powers a load)
  - Negative: Charging (battery is being charged)

### Live Statistics Panel
- **Current Charge**: Real-time battery charge percentage
- **Remaining Energy**: Available energy in Watt-hours
- **Power Flow**: Current power draw or charge rate
- **Runtime/Charge Time**: Estimated time until empty or full
- **Status**: Current battery state (Charging/Discharging/Idle/Full/Empty)

### Visualizations
- **Battery Charge Over Time**: Line graph showing charge level with warning zones
- **Power Flow Over Time**: Line graph displaying power consumption/charging

## License

MIT License - See LICENSE file for details

## Author

FireSon

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.