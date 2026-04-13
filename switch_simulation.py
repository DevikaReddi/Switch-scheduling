"""
==============================================================================
Assignment: Evaluating Network Switch Scheduling Algorithms
==============================================================================
3x3 Crossbar Switch  |  Inputs: I0, I1, I2  |  Outputs: O0, O1, O2

Parts implemented:
  Part 1 - Standard FIFO Queue with Head-of-Line (HoL) Blocking detection
  Part 2 - Virtual Output Queuing (VOQ) with Exhaustive Optimal Search
  Part 3 - VOQ with iSLIP Scheduling  *** MULTI-ITERATION VERSION ***
  Part 4 - Data Visualisation (bar chart + backlog-over-time line graph)

Run:     python switch_scheduler.py
Requires: matplotlib   (pip install matplotlib)

iSLIP multi-iteration note
--------------------------
In each time slot iSLIP runs up to MAX_ITER rounds of REQUEST→GRANT→ACCEPT.
After round k an input/output that was already matched is removed from
contention; unmatched inputs/outputs compete again in round k+1.
Pointers advance only for accepted pairs (unchanged rule).
Using MAX_ITER = N guarantees that, whenever a maximal matching exists,
it is found within N rounds — matching the throughput of the Exhaustive
Optimal Search in most practical cases.
==============================================================================
"""

from collections import deque, defaultdict
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

N = 3           # switch dimensions (3x3)
MAX_ITER = N    # iSLIP iterations per time slot (set to N for best results)

# ── Input trace ───────────────────────────────────────────────────────────────
PACKETS = [
    ("p1",  0, 0, 0), ("p2",  0, 0, 1), ("p3",  0, 1, 0),
    ("p4",  0, 1, 2), ("p5",  0, 2, 0), ("p6",  1, 0, 2),
    ("p7",  1, 2, 1), ("p8",  2, 1, 1), ("p9",  2, 2, 2),
    ("p10", 3, 0, 1), ("p11", 3, 1, 0), ("p12", 3, 2, 1),
    ("p13", 4, 0, 0), ("p14", 4, 1, 2), ("p15", 4, 2, 2),
    ("p16", 5, 0, 2), ("p17", 5, 1, 1), ("p18", 5, 2, 0),
]
TOTAL = len(PACKETS)  # 18

_arrivals = defaultdict(list)
for _pid, _arr, _src, _dst in PACKETS:
    _arrivals[_arr].append((_pid, _src, _dst))


def banner(title):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


# ==============================================================================
# PART 1 - Standard FIFO with Head-of-Line (HoL) Blocking
# ==============================================================================
def part1_fifo():
    """
    Architecture : one FIFO queue per input port.
    Scheduling   : only the HEAD packet of each queue may contend for switching.
    Tie-break    : lowest-numbered input wins when multiple heads want the
                   same output (e.g. I0 beats I1).
    HoL blocking : detected when the head is blocked AND at least one packet
                   BEHIND it in the same queue could have used a FREE output
                   that went unused this slot.
    Backlog      : recorded AFTER arrivals, BEFORE transmission.
    """
    banner("PART 1: Standard FIFO Queue & Head-of-Line (HoL) Blocking")

    queues = [deque() for _ in range(N)]
    sent   = 0
    t      = 0
    backlog_series = []

    while sent < TOTAL:
        for pid, src, dst in _arrivals.get(t, []):
            queues[src].append((pid, dst))

        contention = defaultdict(list)
        for i in range(N):
            if queues[i]:
                _, head_dst = queues[i][0]
                contention[head_dst].append(i)

        used_in, used_out = set(), set()
        granted = {}
        for out in range(N):
            for inp in sorted(contention.get(out, [])):
                if inp not in used_in and out not in used_out:
                    granted[inp] = out
                    used_in.add(inp)
                    used_out.add(out)
                    break

        free_outputs = set(range(N)) - used_out

        sent_this = []
        for inp in range(N):
            if not queues[inp]:
                continue
            head_pid, head_dst = queues[inp][0]
            if inp in granted:
                queues[inp].popleft()
                sent_this.append((inp, head_pid, head_dst))
                sent += 1
            else:
                for behind_pid, behind_dst in list(queues[inp])[1:]:
                    if behind_dst in free_outputs:
                        print(f"  [HOL BLOCKING t={t}] "
                              f"I{inp}: '{head_pid}'->O{head_dst} is BLOCKED. "
                              f"'{behind_pid}'->O{behind_dst} stuck behind it "
                              f"but O{behind_dst} is FREE this slot -- wasted!")
                        break

        # Backlog AFTER transmission: packets remaining after slot t completes
        backlog = sum(len(q) for q in queues)
        backlog_series.append((t, backlog))

        sent_str = (", ".join(f"{pid}(I{i}->O{d})" for i, pid, d in sent_this)
                    if sent_this else "-- nothing sent")
        print(f"  t={t:>2}:  {sent_str}")
        t += 1

    tst = t
    print(f"\n  >> FIFO Total Service Time = {tst} slots  (slots t=0..{t-1})")
    return tst, backlog_series


# ==============================================================================
# PART 2 - Virtual Output Queuing (VOQ) -- Exhaustive Optimal Search
# ==============================================================================
def _all_matchings(voq):
    avail = [(i, j) for i in range(N) for j in range(N) if voq[i][j]]
    result = []

    def backtrack(idx, used_i, used_o, cur):
        if cur:
            result.append(tuple(cur))
        for k in range(idx, len(avail)):
            ii, jj = avail[k]
            if ii not in used_i and jj not in used_o:
                cur.append((ii, jj))
                backtrack(k + 1, used_i | {ii}, used_o | {jj}, cur)
                cur.pop()

    backtrack(0, set(), set(), [])
    return result or [()]


def part2_voq_optimal():
    banner("PART 2: VOQ -- Exhaustive Optimal Search")

    voq  = [[deque() for _ in range(N)] for _ in range(N)]
    sent = 0
    t    = 0
    backlog_series = []

    while sent < TOTAL:
        for pid, src, dst in _arrivals.get(t, []):
            voq[src][dst].append(pid)

        backlog = sum(len(voq[i][j]) for i in range(N) for j in range(N))
        if backlog == 0:
            t += 1
            continue

        all_m = _all_matchings(voq)
        best  = max(all_m, key=lambda m: (
            len(m),
            sum(len(voq[i][j]) for i, j in m)
        ))

        sent_this = []
        for inp, out in best:
            pid = voq[inp][out].popleft()
            sent_this.append((inp, pid, out))
            sent += 1

        # Backlog AFTER transmission: packets remaining after slot t completes
        backlog = sum(len(voq[i][j]) for i in range(N) for j in range(N))
        backlog_series.append((t, backlog))

        sent_str = (", ".join(f"{pid}(I{i}->O{j})" for i, pid, j in sent_this)
                    if sent_this else "-- nothing sent")
        print(f"  t={t:>2}:  Matching {str(list(best)):<32} -> {sent_str}")
        t += 1

    tst = t
    print(f"\n  >> Optimal VOQ Total Service Time = {tst} slots  (slots t=0..{t-1})")
    return tst, backlog_series


# ==============================================================================
# PART 3 - VOQ with iSLIP Scheduling  (MULTI-ITERATION)
# ==============================================================================
def _rr_pick(ptr, candidates):
    """Round-robin: start scanning at ptr, return first idx found in candidates."""
    for offset in range(N):
        idx = (ptr + offset) % N
        if idx in candidates:
            return idx
    return None


def part3_islip():
    """
    Architecture : same VOQ as Part 2.
    Scheduling   : iSLIP algorithm, MAX_ITER iterations per time slot.

    Each iteration is a 3-phase round:
      REQUEST : Unmatched input i requests output j iff voq[i][j] is non-empty
                AND output j is not yet matched this slot.
      GRANT   : Unmatched output j picks the FIRST requesting input starting
                from grant_ptr[j] (round-robin over inputs 0,1,2).
      ACCEPT  : Unmatched input i picks the FIRST granted output starting
                from accept_ptr[i] (round-robin over outputs 0,1,2).

    After ACCEPT, matched input/output pairs are locked for the rest of
    the slot; subsequent iterations only involve still-unmatched ports.

    Pointer update rule (unchanged from single-iteration iSLIP):
      grant_ptr[j]  <- (accepted_input  + 1) mod N  — updated each iteration
      accept_ptr[i] <- (accepted_output + 1) mod N  — updated each iteration

    Using MAX_ITER = N ensures a maximal matching is always found.
    All pointers start at 0.
    """
    banner(f"PART 3: VOQ with iSLIP Scheduling  [{MAX_ITER} iterations/slot]")

    voq        = [[deque() for _ in range(N)] for _ in range(N)]
    grant_ptr  = [0] * N   # grant_ptr[output]  = RR start over inputs
    accept_ptr = [0] * N   # accept_ptr[input]  = RR start over outputs
    sent       = 0
    t          = 0
    backlog_series = []

    while sent < TOTAL:
        # 1. Arrivals
        for pid, src, dst in _arrivals.get(t, []):
            voq[src][dst].append(pid)

        backlog = sum(len(voq[i][j]) for i in range(N) for j in range(N))
        if backlog == 0:
            t += 1
            continue

        print(f"  +-- t={t}  grant_ptr={grant_ptr}  accept_ptr={accept_ptr}")

        # Slot-level matching accumulator
        slot_accepted = {}   # input -> output  (final match for this slot)

        for iteration in range(1, MAX_ITER + 1):
            # Ports already matched this slot are excluded from this iteration
            matched_inputs  = set(slot_accepted.keys())
            matched_outputs = set(slot_accepted.values())

            # ── REQUEST ──────────────────────────────────────────────────────
            # Unmatched input i requests unmatched output j if voq[i][j] non-empty
            requests = defaultdict(set)   # output -> set of requesting inputs
            for i in range(N):
                if i in matched_inputs:
                    continue
                for j in range(N):
                    if j not in matched_outputs and voq[i][j]:
                        requests[j].add(i)

            if not any(requests.values()):
                print(f"  |   iter {iteration}: no new requests — stopping early")
                break

            req_str = {j: sorted(s) for j, s in requests.items() if s}
            print(f"  |   iter {iteration} REQUEST  (out<-inputs): {req_str}")

            # ── GRANT ─────────────────────────────────────────────────────────
            output_grant = {}   # output -> input it grants
            for j in range(N):
                if j in matched_outputs:
                    continue
                if requests[j]:
                    chosen = _rr_pick(grant_ptr[j], requests[j])
                    output_grant[j] = chosen
            print(f"  |   iter {iteration} GRANT   (out->in):     {output_grant}")

            # invert: input -> list of outputs that granted it
            grants_recv = defaultdict(list)
            for j, i in output_grant.items():
                grants_recv[i].append(j)

            # ── ACCEPT ────────────────────────────────────────────────────────
            iter_accepted = {}   # input -> output accepted this iteration
            for i in range(N):
                if i in matched_inputs:
                    continue
                if grants_recv[i]:
                    chosen = _rr_pick(accept_ptr[i], set(grants_recv[i]))
                    iter_accepted[i] = chosen
            print(f"  |   iter {iteration} ACCEPT  (in->out):     {iter_accepted}")

            if not iter_accepted:
                print(f"  |   iter {iteration}: no accepts — stopping early")
                break

            # ── UPDATE POINTERS (accepted pairs only) ─────────────────────────
            for i, j in iter_accepted.items():
                grant_ptr[j]  = (i + 1) % N
                accept_ptr[i] = (j + 1) % N

            # Lock these pairs for the rest of the slot
            slot_accepted.update(iter_accepted)

            print(f"  |   iter {iteration} PTRS: grant_ptr={grant_ptr}  accept_ptr={accept_ptr}")

            # If all ports are matched we can stop early
            if len(slot_accepted) == N:
                break

        # ── TRANSMIT all matched pairs ────────────────────────────────────────
        sent_this = []
        for i, j in slot_accepted.items():
            pid = voq[i][j].popleft()
            sent_this.append((i, pid, j))
            sent += 1

        sent_str = (", ".join(f"{pid}(I{i}->O{j})" for i, pid, j in sent_this)
                    if sent_this else "-- nothing sent")
        print(f"  |   SENT:     {sent_str}")
        print(f"  +--" + "-" * 60)

        # Backlog AFTER transmission: packets remaining after slot t completes
        backlog = sum(len(voq[i][j]) for i in range(N) for j in range(N))
        backlog_series.append((t, backlog))

        t += 1

    tst = t
    print(f"\n  >> iSLIP ({MAX_ITER} iter/slot) Total Service Time = {tst} slots  (slots t=0..{t-1})")
    return tst, backlog_series


# ==============================================================================
# PART 4 - Data Visualisation
# ==============================================================================
def part4_visualise(fifo_tst, voq_tst, islip_tst,
                    fifo_bl, voq_bl, islip_bl):
    banner("PART 4: Data Visualisation")

    fig = plt.figure(figsize=(13, 10))
    fig.suptitle(
        f"Network Switch Scheduling Algorithm Comparison\n"
        f"3x3 Crossbar Switch — 18-Packet Input Trace  "
        f"[iSLIP: {MAX_ITER} iterations/slot]",
        fontsize=13, fontweight="bold", y=0.98
    )
    gs = gridspec.GridSpec(2, 1, hspace=0.52, top=0.90, bottom=0.07)

    COLORS = {
        "FIFO":        "#e74c3c",
        "Optimal VOQ": "#2ecc71",
        f"iSLIP VOQ\n({MAX_ITER} iter)": "#3498db",
    }

    # -- Graph 1: Bar Chart - Total Service Time --------------------------------
    ax1 = fig.add_subplot(gs[0])
    labels = list(COLORS.keys())
    values = [fifo_tst, voq_tst, islip_tst]
    bars   = ax1.bar(labels, values,
                     color=list(COLORS.values()),
                     edgecolor="black", linewidth=0.8, width=0.45)
    for bar, val in zip(bars, values):
        ax1.text(bar.get_x() + bar.get_width() / 2.0, val + 0.1,
                 str(val), ha="center", va="bottom",
                 fontsize=13, fontweight="bold")
    ax1.set_title(
        "Graph 1: Total Service Time — slots needed to empty the switch",
        fontsize=11, pad=8)
    ax1.set_ylabel("Time Slots")
    ax1.set_ylim(0, max(values) + 2)
    ax1.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax1.grid(axis="y", linestyle="--", alpha=0.55)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    # -- Graph 2: Line Graph - Backlog over Time --------------------------------
    ax2 = fig.add_subplot(gs[1])

    def to_xy(bl):
        return [t for t, _ in bl], [c for _, c in bl]

    ft,  fc  = to_xy(fifo_bl)
    vt,  vc  = to_xy(voq_bl)
    it_, ic  = to_xy(islip_bl)

    ax2.plot(ft,  fc,  "o-", color=COLORS["FIFO"],
             label=f"FIFO (TST={fifo_tst})", linewidth=2, markersize=6)
    ax2.plot(vt,  vc,  "s-", color=COLORS["Optimal VOQ"],
             label=f"Optimal VOQ (TST={voq_tst})", linewidth=2, markersize=6)
    ax2.plot(it_, ic,  "^-", color=list(COLORS.values())[2],
             label=f"iSLIP VOQ {MAX_ITER}-iter (TST={islip_tst})",
             linewidth=2, markersize=6)

    ax2.set_title(
        "Graph 2: Backlog over Time — packets remaining in switch (before TX each slot)",
        fontsize=11, pad=8)
    ax2.set_xlabel("Time Slot  t")
    ax2.set_ylabel("Packets Remaining")
    ax2.legend(loc="upper right", fontsize=10)
    ax2.grid(linestyle="--", alpha=0.55)
    ax2.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax2.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.savefig("switch_comparison.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  >> Charts saved to switch_comparison.png")


# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    fifo_tst,  fifo_bl  = part1_fifo()
    voq_tst,   voq_bl   = part2_voq_optimal()
    islip_tst, islip_bl = part3_islip()
    part4_visualise(fifo_tst, voq_tst, islip_tst, fifo_bl, voq_bl, islip_bl)

    banner("FINAL SUMMARY")
    print(f"  {'Algorithm':<28} {'Total Service Time':>20}")
    print(f"  {'-'*50}")
    print(f"  {'FIFO':<28} {fifo_tst:>18} slots")
    print(f"  {'Optimal VOQ':<28} {voq_tst:>18} slots")
    print(f"  {f'iSLIP VOQ ({MAX_ITER} iter/slot)':<28} {islip_tst:>18} slots")
    print(f"  {'-'*50}")
    pct = (fifo_tst - voq_tst) / fifo_tst * 100
    print(f"  VOQ vs FIFO improvement   : {fifo_tst - voq_tst} slots ({pct:.0f}% faster)")
    print(f"  iSLIP vs Optimal gap      : {islip_tst - voq_tst} slots")
    print(f"  (iSLIP iterations/slot    : {MAX_ITER}  — change MAX_ITER to tune)")
    print()