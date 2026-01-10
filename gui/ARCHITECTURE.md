# GUI Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                             sirius.py                           │
│                     (Entry Point - 21 lines)                    │
│                                                                 │
│  • Initializes QApplication                                     │
│  • Creates and shows main window                                │
│  • Manages event loop                                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ imports & instantiates
                         ▼
┌───────────────────────────────────────────────────────────┐
│                       main_window.py                      │
│                  (Main Window - 694 lines)                │
│                                                           │
│  PerformanceTesterGUI (QMainWindow)                       │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ INPUT SECTION                                       │  │
│  │  • URL, Method, Headers (dynamic table)             │  │
│  │  • Body Type selector (None/JSON/Form Data)         │  │
│  │  • Form Data table with file uploads                │  │
│  │  • Requests, Concurrency, Timeout                   │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ CONTROL SECTION                                     │  │
│  │  • Run Test / Stop buttons                          │  │
│  │  • Export buttons (JSON/CSV/HTML)                   │  │
│  │  • Progress bar                                     │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ RESULTS TABS                                        │  │
│  │  • Summary (text)                                   │  │
│  │  • Summary Table                                    │  │
│  │  • Time Series                                      │  │
│  │  • Chart (MatplotlibWidget) ─────────┐              │  │
│  │  • Console (debugging logs)          │              │  │
│  └──────────────────────────────────────┼──────────────┘  │
└──────────────┬──────────────────────────┼─────────────────┘
               │                          │
               │ creates                  │ embeds
               │                          │
               ▼                          ▼
┌───────────────────────────┐   ┌─────────────────────────┐
│       worker.py           │   │      widgets.py         │
│  (Worker - 234 lines)     │   │  (Widgets - 61 lines)   │
│                           │   │                         │
│  TestWorker (QThread)     │   │  MatplotlibWidget       │
│  ┌─────────────────────┐  │   │  ┌──────────────────┐   │
│  │ Signals:            │  │   │  │ Figure           │   │
│  │  • finished         │  │   │  │ FigureCanvas     │   │
│  │  • error            │  │   │  │ plot_timeseries()│   │
│  │  • progress         │  │   │  └──────────────────┘   │
│  │  • log              │  │   └─────────────────────────┘
│  └─────────────────────┘  │
│  ┌─────────────────────┐  │
│  │ Methods:            │  │
│  │  • run()            │  │
│  │  • run_test_with_   │  │
│  │    logging()        │  │
│  │  • run_test_with_   │  │
│  │    formdata()       │  │
│  └─────────────────────┘  │
│                           │
│  Features:                │
│  • SSL disabled           │
│  • Auto headers           │
│  • Content-Length calc    │
│  • Error logging          │
│  • Form data support      │
└───────────────────────────┘


Data Flow:
─────────

1. User Input Flow:
   User → Main Window → Input widgets → Validation

2. Test Execution Flow:
   Main Window → TestWorker (background thread) → HTTP requests
                     │                                    │
                     ├─ Progress signals ─────→ Progress bar
                     ├─ Log signals ─────────→ Console tab
                     └─ Finished signal ──────→ Results display

3. Results Display Flow:
   TestWorker results → Main Window → Process with sirius.py
                                    ↓
                        ┌───────────┴───────────┐
                        │                       │
                   Display tabs          MatplotlibWidget
                   • Summary                • Charts
                   • Tables
                   • Time series

4. Export Flow:
   Main Window → sirius.py functions → Files (JSON/CSV/HTML)


Dependencies:
────────────

performance_tester_gui.py
    └─> main_window.py
            ├─> worker.py
            │       └─> aiohttp (HTTP requests)
            │       └─> asyncio (concurrency)
            │       └─> ssl (SSL configuration)
            │
            ├─> widgets.py
            │       └─> matplotlib (optional - charts)
            │
            └─> sirius.py (parent directory)
                    └─> Performance testing functions


Thread Safety:
─────────────

• Main Thread: UI operations (main_window.py, widgets.py)
• Worker Thread: HTTP requests (worker.py)
• Signals/Slots: Thread-safe communication between threads


Key Design Decisions:
────────────────────

1. Separation of Concerns:
   - UI logic in main_window.py
   - Background processing in worker.py
   - Visualization in widgets.py

2. Signal-Slot Pattern:
   - TestWorker emits signals
   - Main window connects to signals
   - Non-blocking UI updates

3. Optional Dependencies:
   - matplotlib is optional
   - Graceful degradation if not installed

4. Browser-like Behavior:
   - SSL verification disabled
   - Auto-added headers (Host, Connection, etc.)
   - Matches Bruno/Postman behavior
```
