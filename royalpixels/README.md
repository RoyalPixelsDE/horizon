# Horizon als Seed-Generator

Stand 27.10.2026. Horizon (github.com/ludovic111/horizon) ist ein Minecraft-26.3-Server in Rust. Hier steht, wie nah
seine Welten an Vanilla sind, was noch abweicht, wie schnell er ist und wie man die Prüfungen wiederholt. Der Bericht
mit allen Zahlen ist `worldgen-comparison-3seeds-v3.pdf`. Getestet wurde der Testbuild
[royalpixels-2026-10-27](https://github.com/RoyalPixelsDE/horizon/releases/tag/royalpixels-2026-10-27).

## Ergebnis

Seeds 12345, 1 und 8675309, je 1.024 × 1.024 Blöcke in allen drei Dimensionen, Ticks eingefroren.

| | Zweiter Vanilla-Lauf | Paper + Chunky | Horizon |
|---|---|---|---|
| Blöcke anders, Overworld | 0,17 % | 0,34 % | 0,15 % |
| Blöcke anders, Nether | 0,32 % | 0,65 % | 0,23 % |
| End | gleich | 24 Blöcke | gleich |
| Gleicher Loot | – | 99,1 % | 99,4 % |
| Zeit, 3 Seeds × 3 Dimensionen | – | 125 s | 79 s (`/pregen`) |
| RAM beim Generieren | – | 7,3 GB (Heap fest 8 GB) | 1,1 GB |
| RAM im Betrieb, Leerlauf / 16 × 16 Chunks geladen | Vanilla 0,58 / 0,81 GB | 1,03 / 1,10 GB | 0,53 / 0,57 GB |

CPU-Zeit pro Welt ist bei Horizon und Paper etwa gleich (167 s gegen 163 s pro Seed). Horizon ist bei der Wandzeit
schneller, weil es die Kerne besser auslastet: 2.000 × 2.000 Blöcke Overworld in 36 s, 443 Chunks/s.

## Speedrun-Prüfungen ohne Toleranz

Strongholds (jeweils 528 × 528 Blöcke um den nächsten Stronghold), Festung und Bastion der drei Seeds. Ein zweiter
Vanilla-Lauf zeigt, was Vanilla selbst von Lauf zu Lauf ändert. Rohdaten in `werkzeuge/ergebnisse/`.

| Prüfung | Horizon gegen Vanilla |
|---|---|
| Spawnpunkt | gleich, alle 3 Seeds (dazu 60 von 60 Seeds im World-Spawn-Test von Horizon) |
| Stronghold: Start, alle Blöcke der Teile, 12 Endportal-Rahmen mit Augen, Truhen, Spawner | gleich, alle 3 Seeds |
| Bastion: Start, Blöcke, Truhen, Spawner, alle Mobs mit Feldern | gleich, alle 3 Seeds (eine Feuer-Abweichung in Seed 1 hat auch Vanilla selbst) |
| Festung: Start, Truhen, Spawner | gleich, alle 3 Seeds |
| Festung: Blöcke | Seed 12345: 1 Truhe zeigt nach Westen statt nach Süden. Die Ausrichtung hängt auch in Vanilla von der Ladereihenfolge ab (Seed 1 Nether, zwei Vanilla-Läufe verschieden), in 751 Truhen kein Fall nur bei Horizon. Seed 1: 310 Basalt- und Erzblöcke anders, Vanilla selbst 837 (Rauschen). Seed 8675309: 1 Pilz, Vanilla selbst auch |
| Jeder Chunk im erzeugten Gebiet ist `full` und belichtet, auch der äußerste Ring | ja, Forceload und `/pregen`, bis 2.000 × 2.000 Blöcke |

## Offene Unterschiede

Fehler in Horizon, jeweils gegen Vanilla 26.3 geprüft und upstream gemeldet:

| Issue | Was |
|---|---|
| [#2783](https://github.com/ludovic111/horizon/issues/2783) | Mobs aus `/summon`, Eiern, natürlichem Spawnen und Spawnern bekommen ein verkürztes `finalizeSpawn`: Wither-Skelette 2,0 statt 4,0 Schaden, keine Sound-Varianten, keine Babys, falsche Jockeys |
| [#2784](https://github.com/ludovic111/horizon/issues/2784) | Neutrale Mobs vergessen ihre Wut beim Entladen (`anger_end_time`, `angry_at`) |
| [#2785](https://github.com/ludovic111/horizon/issues/2785) | `/forceload`: die 2 Ringe um einen Chunk werden nicht fertig. Daher 427 statt 476 Structure-Starts |
| [#2786](https://github.com/ludovic111/horizon/issues/2786) | Veraltetes Block- und Himmelslicht an Chunk-Grenzen (Luft 0 neben Luft 6) |
| [#2787](https://github.com/ludovic111/horizon/issues/2787) | `/summon` und Spawn-Eier setzen `PersistenceRequired` |
| [#2788](https://github.com/ludovic111/horizon/issues/2788) | Truhen-Ausrichtung und Mineshaft-Boden prüfen Kollision statt `isSolidRender` (nur im Code, kein Fall in unseren Welten) |
| [#2789](https://github.com/ludovic111/horizon/issues/2789) | `CatSpawner` fehlt |
| [#2790](https://github.com/ludovic111/horizon/issues/2790) | `VillageSiege` fehlt |

Kein Fehler, aber anders: `/pregen` dekoriert in anderer Reihenfolge als Vanilla mit `/forceload` (Seed 12345 0,43 %
Blöcke anders statt 0,32 %, zweiter Vanilla-Lauf 0,35 %). Chunky in Paper hat dasselbe. Horizon speichert dunkle
Himmelslicht-Arrays, die Vanilla weglässt (gleiche Werte).

Rauschen, das ein zweiter Vanilla-Lauf genauso zeigt: Structure-Start-Flags am Gebietsrand (8 von 427), Bienennester,
Sculk in der Ancient City, Tiere in einzelnen Chunks, Zufallswerte einzelner Entities (`random_spawn_bonus`,
`EggLayTime`).

Noch nicht geprüft: mehr als 3 Seeds, Buried Treasure, Shipwrecks, Dörfer, Ruined Portals, Blockabweichungen nach
Typ und innerhalb oder außerhalb von Strukturen, Paper auf großer Fläche.

## Performance: was noch drin ist

So verteilt sich Horizons CPU-Zeit in der Overworld: Rohgenerierung 67 % (Noise 43 %, Oberflächenregeln 35 %,
Strukturen 9 %, Höhlen 6 %, Biome 6 %), Dekoration 21 %, Licht 11 %, Fertigstellen 4 %. Mit 11 statt 1 Thread wird
jeder Chunk 1,6- bis 1,8-mal teurer (Hyperthreads, Speicherbandbreite). Gewinne kommen also aus weniger Arbeit pro
Chunk.

| Hebel | Ersparnis Gesamt-CPU, geschätzt | Aufwand |
|---|---|---|
| Oberflächenregeln: tiefe Blöcke vorab auflösen, Biom-IDs statt Strings, reine Höhenbedingungen vorab, Regeln pro Chunk cachen | 8–12 % (Nether-Oberfläche bis −60 %) | mittel |
| Noise: Spalten- und 2D-Werte cachen, SIMD für Dichtefunktionen, Aquifer | 3–10 % | hoch |
| Dekoration: teuerste Features (Bäume, Erze) | 2–5 % | mittel |
| Licht: leere Sektionen überspringen, weniger Doppelarbeit am Rand | 2–4 % | mittel |
| Region-Dateien ohne Kompression (wie unser Paper) | wenig CPU, schnellere Saves | klein |
| Nether und End parallel zur Overworld | ~10 % Wandzeit | klein |

Realistisch 20–35 % weniger CPU. So vorgehen: einen echten Profiler nutzen (`perf` oder `samply`, im LXC gesperrt),
jede Änderung mit `chunkgen_bench` messen, mit `chunkgen_bench --snapshot` vorher und nachher beweisen, dass die Welt
Byte für Byte gleich bleibt, und jede Optimierung als eigenen PR einreichen (Beispiel: horizon#2706).

## Upstream

Gemergt: #2070–#2078, #2434, #2436–#2439, #2449, #2450, #2541, #2543, #2585, #2619. Der Maintainer übernimmt #2544
und #2586 selbst in #2698. Offen: #2608 (leerer Server hält nichts um den Spawn), #2706 (Performance), #2716 (doppelter
Kaninchen-Zweig bricht Clippy auf main).

## Werkzeuge

Alles in `werkzeuge/`. Die Skripte erwarten `~/worldgen-cmp` mit `dl/` (JDK, Server-Jars, Horizon-Builds) und `runs/`.

```
python3 -I gen.py vanilla|paper|horizon SEED RADIUS ZIEL [--pregen] [--boxes boxes.json] [--dims 0,1,2]
python3 -I compare.py VANILLA/world ANDERE/world OUT.json --radius RADIUS --jobs 10
python3 -I entity_fields.py VANILLA/world ANDERE/world        # Felder aller Entities
python3 -I animals.py VANILLA/world ANDERE/world 15             # Tiere pro Chunk
python3 -I area_status.py WELT RADIUS                           # jeder Chunk full und belichtet
python3 -I speedrun_check.py VANILLA/world ANDERE/world boxes.json
./speedrun_gen.sh                                               # Stronghold-, Festungs- und Bastions-Boxen erzeugen
python3 -I ram_idle.py vanilla|paper|horizon ZIEL                # RAM im Betrieb
python3 -I summon_check.py LAUF_A LAUF_B                        # /summon-Felder zweier laufender Server (#2783)
python3 -I forced_rings.py vanilla|horizon SEED ZIEL            # Chunk-Status um einen Forceload-Chunk (#2785)
python3 -I light_at.py DIM X,Y,Z ... -- WELT ...                 # gespeichertes Licht an Positionen (#2786)
python3 -I struct_check.py VANILLA/world ANDERE/world            # Shipwrecks, Buried Treasure, Dörfer, Ruined Portals
./r3.sh none && python3 -I report_r4.py                         # 3-Seed-Vergleich und PDF
```

`GEN_SPAWN_MOBS=1` lässt Mob-Spawning beim Generieren an (wie unser Seed-Generator). `GEN_TICKING=1` lässt die Ticks
laufen.
