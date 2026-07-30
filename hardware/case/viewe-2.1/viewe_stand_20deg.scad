// VIEWE UEDX48480021 desk case
// Flat anti-tip base. Display seat at tilt_deg from vertical.
// Chip bay sized for measured board + pin-header clearance.
// USB-C on the chip is RIGHT edge, upper, VERTICAL (alto y delgado).
// Case hole is a tall thin slot on the REAR wall aligned to that port.
//
// Export from OpenSCAD GUI: Design → Render (F6) → File → Export → STL
//   part="stand"  → stand body
//   part="cover"  → top hatch cover

/* [Which part] */
part = "stand"; // "stand" | "cover" | "preview"

/* [Display — datasheet outline φ80]
   Measured body depth excluding the 2 paticas: 30 mm. */
display_od     = 80.0;
clear_r        = 0.5;
lip            = 1.8;
display_body_d = 30.0;
pocket_d       = display_body_d + 0.6;
tilt_deg       = 20.0;

/* [Rear steps + 2 paticas — ring slot, positions not exact] */
tier_mid_d  = 52.0;
tier_mid_h  = 10.0;
tier_top_d  = 30.0;
tier_top_h  = 8.0;
peg_ring_ri = 5.0;
peg_ring_ro = 15.0;
peg_slot_d  = 4.0;

/* [USB adapter — measured USB-test-MD50-V3.3]
   PCB 44×37×1 mm.
   Silk view: USB-C on RIGHT edge (upper), FPC on BOTTOM, 10-pin header on LEFT,
   UART pins bottom-right, 3 holes TL/TR/BL.
   In the case: board on edge, USB face REAR, pin header toward the display
   with real clearance for the header plastic/pins. */
board_y      = 44.0;  // left pins → right USB (depth)
board_z      = 37.0;  // bottom FPC → top
board_th     = 1.0;
// component side: USB shell + room if pin headers are populated
board_comp   = 10.0;
board_clear  = 0.6;
// extra beyond PCB outline for pin-header plastic on the LEFT edge
pin_clear_y  = 4.0;
pin_clear_z  = 3.0;  // UART row / FPC latch
hole_inset   = 3.0;
usb_overhang = 2.0;
post_od      = 4.2;
post_id      = 2.0;
post_h       = 3.0;  // standoff; components sit in board_comp pocket

/* [USB-C rear exit]
   On the chip the receptacle is VERTICAL (alto y delgado) on the right edge.
   Cutout must be taller in Z than wide in X — not a landscape slot. */
usb_w = 9.0;   // thin (across board thickness / X)
usb_h = 14.0;  // tall (along board edge / Z) — room for cable mold
fpc_w = 14.0;
fpc_h = 1.6;

/* [Shell / anti-tip base] */
wall       = 2.8;
base_th    = 4.0;
toe_front  = 32.0;
heel_rear  = 36.0;
base_widen = 10.0;

/* [Finish / preview color]
   STL has no color — print with cyan/sky-blue PLA to match the desk LEDs.
   This only tints the OpenSCAD preview. */
preview_rgb = [0.15, 0.72, 0.95]; // electric cyan ≈ keyboard/mouse glow

$fn = 64;
eps = 0.08;

view_d   = display_od - 2 * lip;
cradle_d = display_od + 2 * clear_r;
shell_w  = max(cradle_d + 2 * wall + 8, 44 + 30);
shell_h  = max(cradle_d + 2 * wall + 8, 37 + 30);

// Bay: thickness along X; USB at +Y; pin header toward -Y (display)
bay_w = board_th + board_comp + post_h + 2 * board_clear;
bay_d = pin_clear_y + board_y + usb_overhang + board_clear;
bay_h = board_z + 2 * pin_clear_z + 2 * board_clear;

body_d = pocket_d + peg_slot_d + 2 + bay_d + wall;
lift   = body_d * sin(tilt_deg);

bay_y0 = pocket_d + peg_slot_d + 2;
bay_x0 = -bay_w / 2;                 // centered — NOT shoved to case corner
bay_z0 = (shell_h - bay_h) / 2;

// PCB plane: after posts from left wall; pins face -Y into pin_clear_y pocket
pcb_x = bay_x0 + board_clear + post_h;
pcb_y0 = bay_y0 + pin_clear_y;       // board starts after pin clearance

if (part == "stand") color(preview_rgb) stand();
else if (part == "cover") color(preview_rgb) top_cover();
else {
  color(preview_rgb) stand();
  translate([shell_w + 25, 0, 0]) color(preview_rgb) top_cover();
}

// ---------------------------------------------------------------------------
module stand() {
  difference() {
    union() {
      flat_base();
      under_fill();
      translate([0, toe_front, base_th + lift])
        rotate([-tilt_deg, 0, 0])
          seat_body();
    }
    translate([-300, -300, -100]) cube([600, 600, 100]);
  }
}

module flat_base() {
  base_d = toe_front + body_d * cos(tilt_deg) + heel_rear;
  base_w = shell_w + 2 * base_widen;
  translate([-base_w / 2, 0, 0])
    cube([base_w, base_d, base_th]);
}

module under_fill() {
  hull() {
    translate([-shell_w / 2, toe_front, base_th])
      cube([shell_w, 0.1, 0.1]);
    translate([-shell_w / 2, toe_front + body_d * cos(tilt_deg), base_th])
      cube([shell_w, 0.1, 0.1]);
    translate([-shell_w / 2, toe_front, base_th + lift])
      cube([shell_w, 0.1, 0.1]);
  }
}

module seat_body() {
  cx = 0;
  cz = shell_h / 2;

  difference() {
    translate([-shell_w / 2, 0, 0])
      cube([shell_w, body_d, shell_h]);

    // display pocket 30 mm body
    translate([cx, -eps, cz])
      rotate([-90, 0, 0])
        cylinder(d = cradle_d, h = pocket_d + eps);
    translate([cx, -eps, cz])
      rotate([-90, 0, 0])
        cylinder(d = view_d, h = wall + 1);

    // stepped reliefs inside the 30 mm
    translate([cx, pocket_d - tier_mid_h - tier_top_h, cz])
      rotate([-90, 0, 0])
        cylinder(d = tier_mid_d + 1.0, h = tier_mid_h + tier_top_h + eps);
    translate([cx, pocket_d - tier_top_h, cz])
      rotate([-90, 0, 0])
        cylinder(d = tier_top_d + 1.0, h = tier_top_h + eps);

    // paticas ring beyond 30 mm
    translate([cx, pocket_d - eps, cz])
      rotate([-90, 0, 0])
        difference() {
          cylinder(d = 2 * peg_ring_ro, h = peg_slot_d);
          translate([0, 0, -eps])
            cylinder(d = 2 * peg_ring_ri, h = peg_slot_d + 2 * eps);
        }

    // chip bay — includes pin_clear_y toward the display for the 10-pin header
    translate([bay_x0, bay_y0, bay_z0])
      cube([bay_w, bay_d, bay_h]);

    // EXIT 1: USB-C rear — VERTICAL slot (tall Z, thin X), upper half of right edge
    translate([
      pcb_x + board_th / 2 - usb_w / 2,
      body_d - wall - eps,
      bay_z0 + board_clear + pin_clear_z + board_z * 0.50
    ])
      cube([usb_w, wall + 2 * eps, usb_h]);

    // EXIT 2: FPC from BOTTOM edge of chip toward display hub
    translate([
      pcb_x + board_th / 2 - fpc_w / 2,
      pocket_d - eps,
      bay_z0 + board_clear
    ])
      cube([fpc_w, pcb_y0 - pocket_d + 8, fpc_h + pin_clear_z]);

    // top hatch
    translate([bay_x0 - 0.2, bay_y0 - 0.2, bay_z0 + bay_h - eps])
      cube([bay_w + 0.4, bay_d + 0.4, shell_h - (bay_z0 + bay_h) + wall]);
  }

  board_posts();
}

// 3 posts BL / TL / TR (no bottom-right hole on the PCB)
module board_posts() {
  holes = [
    [hole_inset, hole_inset],
    [hole_inset, board_z - hole_inset],
    [board_y - hole_inset, board_z - hole_inset]
  ];
  for (h = holes)
    translate([bay_x0 - 1.0, pcb_y0 + h[0], bay_z0 + board_clear + pin_clear_z + h[1]])
      rotate([0, 90, 0])
        difference() {
          cylinder(d = post_od, h = post_h + 1.0);
          translate([0, 0, -eps])
            cylinder(d = post_id, h = post_h + 1.0 + 2 * eps);
        }
}

module top_cover() {
  cube([bay_w + 0.4, bay_d + 0.4, wall]);
}
