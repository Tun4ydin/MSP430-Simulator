# Graph Report - msp430sim  (2026-11-06)

## Corpus Check
- 9 files · ~10,853 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: .asm 7)

## Summary
- 247 nodes · 492 edges · 11 communities (5 shown, 6 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 34 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- App
- cpu.py
- asm.py
- test_sim.py
- MSP430
- TimerA
- gui.py
- WDT
- run

## God Nodes (most connected - your core abstractions)
1. `App` - 44 edges
2. `MSP430` - 34 edges
3. `assemble()` - 27 edges
4. `Asm` - 18 edges
5. `run()` - 17 edges
6. `TimerA` - 15 edges
7. `words()` - 12 edges
8. `Encoding` - 12 edges
9. `UART` - 12 edges
10. `Alu` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Sözdizimi` --references--> `main()`  [INFERRED]
  README.md → msp430sim/gui.py
- `build()` --calls--> `assemble()`  [EXTRACTED]
  tests/test_sim.py → msp430sim/asm.py
- `build()` --calls--> `MSP430`  [EXTRACTED]
  tests/test_sim.py → msp430sim/cpu.py
- `words()` --calls--> `assemble()`  [EXTRACTED]
  tests/test_sim.py → msp430sim/asm.py
- `App` --uses--> `MSP430`  [INFERRED]
  msp430sim/gui.py → msp430sim/cpu.py

## Import Cycles
- None detected.

## Communities (11 total, 6 thin omitted)

### Community 1 - "cpu.py"
Cohesion: 0.08
Nodes (4): Periph, Plain, Port, UART

### Community 2 - "asm.py"
Cohesion: 0.14
Nodes (6): Asm, AsmError, _reg(), Result, _split(), _strip_comment()

### Community 3 - "test_sim.py"
Cohesion: 0.13
Nodes (6): assemble(), AsmRobustness, Encoding, Examples, Peripherals, words()

### Community 7 - "gui.py"
Cohesion: 0.14
Nodes (5): main(), MSP430 Simulator (G2553) — kart gerektirmez, Neler var, Sözdizimi, Sınırlar

### Community 10 - "run"
Cohesion: 0.09
Nodes (10): Alu, build(), Cycles, Gui, Programs, PullUp, Reference, run() (+2 more)

## Knowledge Gaps
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `App` connect `App` to `run`, `MSP430`, `.show_help`, `gui.py`?**
  _High betweenness centrality (0.294) - this node is a cross-community bridge._
- **Should `App` be split into smaller, more focused modules?**
  _Cohesion score 0.1141025641025641 - nodes in this community are weakly interconnected._
- **Why does `MSP430` connect `MSP430` to `App`, `cpu.py`, `test_sim.py`, `gui.py`, `run`?**
  _High betweenness centrality (0.244) - this node is a cross-community bridge._
- **Should `cpu.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0846774193548387 - nodes in this community are weakly interconnected._
- **Why does `assemble()` connect `test_sim.py` to `App`, `asm.py`, `run`, `gui.py`?**
  _High betweenness centrality (0.147) - this node is a cross-community bridge._
- **Should `asm.py` be split into smaller, more focused modules?**
  _Cohesion score 0.135632183908046 - nodes in this community are weakly interconnected._
- **Should `test_sim.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1268939393939394 - nodes in this community are weakly interconnected._