# 🔀 Network Switch Scheduling Algorithms

> Simulation and comparison of three scheduling algorithms on a **3×3 crossbar switch** — evaluating throughput, Head-of-Line blocking, and backlog evolution across an 18-packet input trace.

---

## 📌 Overview

This project implements and benchmarks three input-queued switch scheduling algorithms:

| Algorithm | Queue Structure | Scheduling Policy |
|---|---|---|
| **FIFO** | 1 queue per input port | Head-of-Line (HoL) contention |
| **Optimal VOQ** | N×N VOQ matrix | Exhaustive DFS — globally optimal matching |
| **iSLIP VOQ** | N×N VOQ matrix | Multi-iteration round-robin (N iters/slot) |

**Switch configuration:** 3×3 crossbar · Inputs: I0, I1, I2 · Outputs: O0, O1, O2  
**Trace:** 18 packets arriving over time slots t = 0 … 5

---

## 📊 Results Summary

| Algorithm | Total Service Time | vs FIFO |
|---|---|---|
| FIFO (HoL Blocking) | 8 slots | baseline |
| Optimal VOQ (DFS) | 6 slots | **25% faster** |
| iSLIP VOQ (3 iter/slot) | 6 slots | **25% faster** |

- iSLIP with `MAX_ITER = N = 3` matches Optimal VOQ — zero gap on this trace.
- FIFO wastes bandwidth due to HoL blocking events detected at multiple time slots.

---

## 🗂️ Project Structure

```
switch-scheduler/
├── switch_scheduler.py      # Main simulation (Parts 1–4)
├── switch_comparison.png    # Generated chart (bar + line graphs)
└── README.md
```

---

## ⚙️ Requirements

- Python 3.8+
- matplotlib

```bash
pip install matplotlib
```

---

## 🚀 Running the Simulation

```bash
python switch_scheduler.py
```

This will:
1. Run all three scheduling algorithms sequentially
2. Print a slot-by-slot trace to the console (including HoL blocking events)
3. Display a final performance summary
4. Save `switch_comparison.png` with two graphs

---

## 📈 Output

**Console output** includes:
- Slot-by-slot packet transmission log for each algorithm
- HoL blocking events (FIFO only) — which packet was blocked and which output went unused
- iSLIP per-iteration REQUEST / GRANT / ACCEPT / pointer state
- Final summary table

**`switch_comparison.png`** contains:
- **Graph 1 — Bar chart:** Total service time across all three algorithms
- **Graph 2 — Line graph:** Backlog (packets remaining in switch) over time

---

## 🧠 Algorithm Details

### Part 1 — FIFO with HoL Blocking
One FIFO queue per input. Only the head packet contends each slot. Lowest-numbered input wins ties. HoL blocking is detected when a blocked head prevents a behind-it packet from using a free output.

### Part 2 — VOQ with Exhaustive Optimal Search
An N×N VOQ matrix eliminates HoL blocking. A recursive DFS backtracking search enumerates all valid input-output matchings per slot and selects the one with maximum cardinality (ties broken by total queue depth). Optimal for N ≤ 4.

### Part 3 — VOQ with iSLIP (Multi-Iteration)
Same VOQ structure as Part 2. Each time slot runs up to `MAX_ITER = N` rounds of **REQUEST → GRANT → ACCEPT** with round-robin pointer advancement. Matched ports are locked out of subsequent iterations. Guarantees a maximal matching and matches Optimal throughput in practice.

---

## 🔧 Configuration

Inside `switch_scheduler.py`:

```python
N        = 3   # Switch dimension (NxN)
MAX_ITER = N   # iSLIP iterations per time slot — increase for larger switches
```

---

## 📄 License

MIT
