# Rev Gamma plates and enclosure

The repository generates two vendor-ready manufacturing packages. They share
the exact Rev Gamma PCB outline and six M2 mounting positions, but the left and
right parts are separate because the physical halves are mirrored. Do not ask a
vendor to mirror any supplied file.

## Acrylic top and bottom plates

Run `npm run generate:enclosures`, then upload:

```text
output/manufacturing/arc58-acrylic-plates-rev-gamma.zip
```

The package contains left/right DXF cut files, SVG previews, an order README,
and a Choc v1 fit coupon. Specify:

- 1.5 mm cast acrylic for the top switch plates;
- 3.0 mm cast acrylic for the bottom plates;
- one left and one right of each layer;
- millimetres, 1:1 scale, with the vendor's normal laser-kerf compensation;
- no engraving and no automatic geometry repair.

Cut the supplied 13.8/14.0/14.2 mm coupon in the exact material, color, and
machine settings first. The full plate uses the nominal 14.0 mm opening, but
acrylic thickness and laser kerf materially affect Choc switch retention. Do
not release the full decorative plate until the actual switch batch fits the
coupon.

The large rounded Helios/OLED service area and the 17 x 10 mm TRRS cable path
are boolean-merged into one continuous notch through the inner plate edge.
This leaves one unambiguous cut contour and allows a molded cable to be
inserted after assembly. A 12.5 x 12.5 mm square encoder opening clears the
EC11 metal body so the plate can lie flat; the former 7.2 mm round opening
cleared only the threaded shaft. Six 2.4 mm holes clear M2 fasteners. The 4.5
mm bottom opening provides reset access.

## CNC aluminum case

Upload this package to a CNC shop:

```text
output/manufacturing/arc58-cnc-aluminum-case-rev-gamma.zip
```

The selected architecture is a low-profile machined bottom chassis with a
separate switch plate. This keeps USB-C and TRRS access visible above the rim
and avoids hidden side undercuts. The inner rim has an open TRRS cable notch
from Z=4.5 mm through the top, aligned with the same 10 mm-high plate slot. The
switch plate can be either the included 1.5 mm aluminum STEP model or the
acrylic top plate.

Specify:

- 6061-T6 aluminum;
- one left and one right bottom chassis;
- optional one left and one right 1.5 mm aluminum switch plate;
- STEP as the authoritative geometry, millimetres, no scaling or mirroring;
- drill 1.6 mm and tap the six bosses M2 x 0.4 to 4 mm depth;
- general tolerance +/-0.125 mm and mounting/switch locations +/-0.10 mm;
- deburr, with exposed edge breaks no larger than R0.5;
- optional bead blast and anodize; mask and chase threaded holes afterward.

Reference assembly STEP files show the intended relationship between chassis,
PCB envelope, and switch plate. Top-view DXFs and the nominal section SVG are
inspection drawings, not replacements for the STEP geometry.

## Stack and hardware

From bottom to top, the nominal stack is:

1. 2.5 mm aluminum floor or 3.0 mm acrylic bottom plate;
2. at least 3.2 mm clear space below the PCB for hotswap sockets and LEDs;
3. 1.6 mm PCB;
4. 2.2 mm nominal gap from PCB top to switch-plate underside;
5. 1.5 mm acrylic or aluminum switch plate.

Use six M2 fasteners per half. Select screw length only after measuring the
fabricated PCB, sockets, and chosen plate stack; the model intentionally does
not prescribe a decorative external screw head or rubber-foot system.

## Prototype requirement

These packages are mechanically checked and the STEP files are re-imported as
valid solids during generation. They remain Rev Gamma: first order one
prototype pair, dry-fit the PCB and switches, and complete
`BRING-UP-CHECKLIST.md` before ordering finished cases in quantity.

Reference dimensions were checked against the official [KEEBD Helios product
page](https://keebd.com/en-us/products/helios-controller), [Kailh PG1350 data
sheet](https://www.kailhswitch.com/Content/upload/pdf/202115927/CPG135001S30-data-sheet.pdf),
and common [CNC machining design guidance](https://di1vc2liilbw2.cloudfront.net/guides/cnc-machining/).
