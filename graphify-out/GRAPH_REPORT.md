# Graph Report - msp430sim  (2026-11-06)

## Corpus Check
- 13 files · ~11,824 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: .asm 7, (none) 1)

## Summary
- 271 nodes · 547 edges · 15 communities (7 shown, 8 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 35 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `456e0db8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- App
- cpu.py
- asm.py
- test_sim.py
- MSP430
- TimerA
- cli.py
- WDT
- UART
- run
- MSP430 Simulator (G2553) — kart gerektirmez
- run.sh script
- msp430sim

## God Nodes (most connected - your core abstractions)
1. `App` - 44 edges
2. `MSP430` - 35 edges
3. `assemble()` - 29 edges
4. `Asm` - 18 edges
5. `run()` - 17 edges
6. `TimerA` - 15 edges
7. `run_cli()` - 14 edges
8. `words()` - 12 edges
9. `Encoding` - 12 edges
10. `UART` - 12 edges

## Surprising Connections (you probably didn't know these)
- `Gui` --uses--> `App`  [INFERRED]
  tests/test_sim.py → msp430sim/gui.py
- `build()` --calls--> `MSP430`  [EXTRACTED]
  tests/test_sim.py → msp430sim/cpu.py
- `main()` --calls--> `find_tk_python()`  [EXTRACTED]
  run.py → msp430sim/cli.py
- `main()` --calls--> `run_cli()`  [EXTRACTED]
  run.py → msp430sim/cli.py
- `main()` --calls--> `main()`  [EXTRACTED]
  run.py → msp430sim/gui.py

## Import Cycles
- None detected.

## Communities (15 total, 8 thin omitted)

### Community 1 - "cpu.py"
Cohesion: 0.09
Nodes (4): Mem, Periph, Plain, Port

### Community 2 - "asm.py"
Cohesion: 0.14
Nodes (6): Asm, AsmError, _reg(), Result, _split(), _strip_comment()

### Community 3 - "test_sim.py"
Cohesion: 0.13
Nodes (8): assemble(), AsmRobustness, build(), Cycles, Encoding, Reference, Symbols, words()

### Community 4 - "MSP430"
Cohesion: 0.12
Nodes (4): MSP430, Examples, Peripherals, Programs

### Community 6 - "cli.py"
Cohesion: 0.19
Nodes (6): find_tk_python(), run_cli(), main(), entry_point(), main(), CommandLine

### Community 10 - "run"
Cohesion: 0.20
Nodes (4): Alu, PullUp, run(), UartTx

### Community 12 - "MSP430 Simulator (G2553) — kart gerektirmez"
Cohesion: 0.29
Nodes (6): Diğer Kullanım Seçenekleri, Hızlı Başlangıç, MSP430 Simulator (G2553) — kart gerektirmez, Neler var, Sözdizimi, Sınırlar

## Knowledge Gaps
- **1 isolated node(s):** `msp430sim`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 71 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `App` connect `App` to `test_sim.py`, `cli.py`, `gui.py`?**
  _High betweenness centrality (0.230) - this node is a cross-community bridge._
- **What connects `msp430sim` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `App` be split into smaller, more focused modules?**
  _Cohesion score 0.08326530612244898 - nodes in this community are weakly interconnected._
- **Why does `MSP430` connect `MSP430` to `App`, `cpu.py`, `test_sim.py`, `cli.py`, `gui.py`?**
  _High betweenness centrality (0.187) - this node is a cross-community bridge._
- **Should `cpu.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09425287356321839 - nodes in this community are weakly interconnected._
- **Why does `assemble()` connect `test_sim.py` to `App`, `asm.py`, `MSP430`, `cli.py`, `gui.py`?**
  _High betweenness centrality (0.141) - this node is a cross-community bridge._
- **Should `asm.py` be split into smaller, more focused modules?**
  _Cohesion score 0.135632183908046 - nodes in this community are weakly interconnected._