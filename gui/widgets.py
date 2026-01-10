"""Custom widgets for the performance tester GUI"""

from typing import List, Dict, Any

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtGui import QFont

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class MatplotlibWidget(QWidget):
    """Widget to display matplotlib charts"""
    def __init__(self, parent=None):
        super().__init__(parent)
        if not MATPLOTLIB_AVAILABLE:
            return
            
        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvas(self.figure)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def plot_timeseries(self, timeseries: List[Dict[str, Any]]):
        """Plot requests/sec and avg latency over time"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        self.figure.clear()
        
        if not timeseries:
            return
        
        seconds = [e['second'] for e in timeseries]
        rps = [e.get('requests_per_second', 0) for e in timeseries]
        avg_lat = [
            e.get('avg_latency_ms') if e.get('avg_latency_ms') is not None 
            else (e.get('avg_latency_s') * 1000.0 if e.get('avg_latency_s') is not None else float('nan'))
            for e in timeseries
        ]

        ax1 = self.figure.add_subplot(111)
        ax1.bar(seconds, rps, color='#3498db', alpha=0.6, label='Requests/sec')
        ax1.set_xlabel('Second (relative)')
        ax1.set_ylabel('Requests/sec', color='#3498db')
        ax1.tick_params(axis='y', labelcolor='#3498db')
        ax1.grid(True, alpha=0.3)

        ax2 = ax1.twinx()
        ax2.plot(seconds, avg_lat, color='#e74c3c', marker='o', linewidth=2, markersize=4, label='Avg latency (ms)')
        ax2.set_ylabel('Avg latency (ms)', color='#e74c3c')
        ax2.tick_params(axis='y', labelcolor='#e74c3c')

        self.figure.tight_layout()
        self.canvas.draw()
