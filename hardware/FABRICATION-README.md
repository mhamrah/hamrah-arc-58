# Arc 58 Rev Gamma fabrication notes

`arc58-reversible-pcb-rev-gamma.zip` contains one two-layer reversible PCB. Order
quantity two; do not mirror the Gerbers at the fabricator. In the assembled
keyboard, B.Cu faces the keycaps on the left half and F.Cu faces the keycaps on
the right half. Follow `hardware/README.md` for the component-side table.

Requested baseline:

- 1.6 mm FR4, two copper layers;
- 1 oz finished copper;
- 0.20 mm minimum track and 0.15 mm minimum spacing;
- mixed 0.40/0.20 mm and 0.60/0.30 mm via diameter/drill, tented on both
  sides;
- at least 0.25 mm annular ring on every plated component hole;
- 0.25 mm copper-to-edge clearance;
- 0.05 mm solder-mask expansion;
- plated through holes plus a separate non-plated drill file; and
- solder mask and silkscreen on both sides.

The `Edge_Cuts` Gerber must show 29 closed profiles: one outer perimeter plus
28 rectangular 3.6 x 3.1 mm RGB apertures. Reject the upload if the fabricator
viewer shows only the outer perimeter. J1 is the horizontal inner-edge TRRS
jack; do not rotate or substitute its footprint.

The archive includes Gerber X2 copper, mask, silkscreen, and edge-cut layers;
separate plated/non-plated Excellon drill files; an IPC-D-356 connectivity
netlist; and a board statistics report. Upload the archive without renaming or
mirroring individual files, inspect every layer in the fabricator's viewer,
and confirm the outline and drill files are recognized before ordering.
Zoom into several switch centers and verify that each RGB aperture is visible.
The 0.60/0.30 mm profile is the default. Compact 0.40/0.20 mm vias are retained
only in dense reversible escape routing where enlarging them causes clearance
violations. The intended fabricator supports this profile but may apply its
small-via surcharge. Do not let the fabricator shrink annular rings without
engineering review.
Also inspect the four thumb switch locator-hole pairs: on the F.Cu/right view
their physical axes must be -10, -30, -45, and -55 degrees from inner to outer;
after mirroring for the B.Cu/left assembly they must be +10, +30, +45, and +55
degrees. The four centers must be 21.25 mm apart, with T1 only 1 mm outward from
the C5/C6 midpoint. The final center step is 45 degrees, placing T4 farther
outward and upward with more than 3.4 mm nominal clearance from T3 when using
the specified 16.5 mm keycaps. Reject any archive whose thumb fan has the
opposite handedness or the former 20.5 mm spacing. Confirm the thumb-bay
mounting hole is between T2 and T3, matching the regenerated plate and case
files.

Confirm each 18 mm encoder knob has equal 9.17 mm clearance to the nearest C6
keycap edge and the curved inner PCB edge. Confirm the relocated inner H4
mounting point matches the regenerated PCB, plate, and case files.

Inspect D26-D29 on both assembly faces. Their bodies must sit tangent to the
thumb fan with clear space between each SOD-123 package and the Choc hotswap
socket. D27 and D29 intentionally sit farther behind their switches where the
reversible COL4 route requires extra assembly clearance; D29's cathode is on
the opposite tangent end from D26-D28. Always follow the local cathode bar.

Run `npm run verify` immediately before regenerating or ordering. A passed DRC
does not replace a physical prototype: order a small first batch and complete
`hardware/BRING-UP-CHECKLIST.md` before a larger run.
