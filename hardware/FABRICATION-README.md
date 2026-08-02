# Arc 58 Rev B fabrication notes

`arc58-reversible-pcb-rev-b.zip` contains one two-layer reversible PCB. Order
quantity two; do not mirror the Gerbers at the fabricator. In the assembled
keyboard, B.Cu faces the keycaps on the left half and F.Cu faces the keycaps on
the right half. Follow `hardware/README.md` for the component-side table.

Requested baseline:

- 1.6 mm FR4, two copper layers;
- 1 oz finished copper;
- 0.15 mm minimum track/space;
- 0.40/0.20 mm finished via diameter/drill;
- 0.25 mm copper-to-edge clearance;
- 0.05 mm solder-mask expansion;
- plated through holes plus a separate non-plated drill file; and
- solder mask and silkscreen on both sides.

The archive includes Gerber X2 copper, mask, silkscreen, and edge-cut layers;
separate plated/non-plated Excellon drill files; an IPC-D-356 connectivity
netlist; and a board statistics report. Upload the archive without renaming or
mirroring individual files, inspect every layer in the fabricator's viewer,
and confirm the outline and drill files are recognized before ordering.

Run `npm run verify` immediately before regenerating or ordering. A passed DRC
does not replace a physical prototype: order a small first batch and complete
`hardware/BRING-UP-CHECKLIST.md` before a larger run.
