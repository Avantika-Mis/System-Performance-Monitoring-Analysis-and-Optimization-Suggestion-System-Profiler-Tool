# System Performance Monitoring and Optimization Profiler Tool

## 🔍 Problem Statement
Modern computing systems often suffer from performance issues due to:
- Inefficient resource utilization
- Sudden CPU/memory spikes
- Disk bottlenecks and network congestion
- Lack of detailed monitoring or platform-independent tools
- No Anomaly detection and optimization suggestion

These issues go unnoticed until they cause app crashes, system slowdowns, or hardware failures. Most users lack tools to proactively detect and resolve such problems.

---

## 💡 Proposed Solution
This project presents a **cross-platform system profiler tool** for Windows and Linux, developed using:
- **Python, Flask** for backend processing
- **Chart.js** for data visualization
- **Isolation Forest** for anomaly detection
- **Random Forest Classifier** for optimization suggestions

### Core Capabilities:
- Real-time and historical monitoring of system metrics (CPU, memory, disk, network)
- Automatic alerts, process termination, or system shutdown on critical issues
- Trend analysis via archived data
- User-friendly dashboard with scheduling and exporting functionality

---

## 📌 Project Scope
- Real-time & historical monitoring
- Cross-platform support (Windows/Linux)
- ML-based anomaly detection
- Optimization recommendations
- User-configurable scan intervals (minutes/hours/days)
- Archiving metrics in `.txt` format

---

## ✅ Functional Requirements

### FR1. Real-time Monitoring
Monitors CPU usage, memory consumption, disk space, and network activity to detect performance bottlenecks and memory leaks.

### FR2. Process Starvation & Garbage Collection
- Detects starvation due to lack of CPU access
- Tracks garbage collection to identify memory leaks or inefficiencies

### FR3. Archival of Observed Data
Allows users to archive metrics based on time thresholds for future trend analysis.

### FR4. User-Friendly Dashboard
Displays visualizations (graphs/charts) for all metrics. Users can filter by resource and time range.

### FR5. Scheduled Scan Interface
Users can set scans to occur every minute, hour, or day with manual override and scan status tracking.

### FR6. Alerts for Abnormal Usage
Alerts triggered on:
- High CPU or memory usage
- Low disk space
- Thread starvation or memory leaks

### FR7. Cross-Platform Compatibility
Compatible with Windows and Linux using platform-agnostic Python libraries.

### FR8. Process Termination & System Shutdown
- Terminates misbehaving processes
- Alerts or shuts down system in case of extreme conditions (e.g., disk full)

### FR9. Analysis and Optimization Suggestions
ML-based recommendations for:
- Thread control
- Memory usage
- CPU-bound code
- Disk I/O and context switch handling

---

## 📈 Optimization Table

| Performance Issue         | Suggested Optimization                             |
|--------------------------|----------------------------------------------------|
| Excessive thread creation | Use thread pools, cap thread count                |
| Leaked/idle threads       | Audit and remove unused threads                   |
| High lock contention      | Minimize critical section, refactor shared states |
| CPU-bound processing      | Use multiprocessing or vectorized operations      |
| High memory usage         | Tune GC, use generators, monitor retention        |
| Heavy disk I/O            | Use buffered I/O, batch transfers                 |
| Context switching         | Cooperative multitasking, thread tuning           |
| Priority imbalance        | Normalize priorities for fair scheduling          |

---

## 🧠 Technologies Used
- Python, Flask
- Chart.js
- Scikit-learn (for Isolation Forest and Random Forest)
- psutil / platform (for system metrics)

---


