"""VIEWE UEDX48480021 desk stand (build123d / cadgen).

Display φ80 × 30 mm (without its 2 rear pegs) sits in a cup tilted 20° back; the base
stays flat. Behind the cup a sealed pod holds the USB adapter (44 × 37 × 1 mm) standing
on edge on 3 screw posts: USB-C exits the pod's rear wall, the display FPC enters
through a round hole in the cup floor. A slide-in lid closes the pod's side.

Local frame (before tilt): origin at the display front centre, +Y into the case,
+Z up the display face, +X to the right seen from the front.
"""

import math

import build123d as bd
from cadgen import model

COLOR = "#1FA2E0"  # cyan blue, matches the desk LEDs
TILT = 20.0  # display face vs vertical
EPS = 0.1

# Display (datasheet φ80, measured depth 30 without the pegs)
DISPLAY_D = 80.0
DISPLAY_DEPTH = 30.0
R_BORE = DISPLAY_D / 2 + 0.5
WALL = 2.4
R_CUP = R_BORE + WALL
Y_RIM = 1.5  # display stands ~1 mm proud of the rim
Y_FLOOR = DISPLAY_DEPTH + 0.4  # hub face rests here
PEG_SLOT = 5.0  # free ring for the 2 pegs (positions unknown)
PEG_RI, PEG_RO = 6.0, 14.5
Y_FLOOR_BACK = Y_FLOOR + PEG_SLOT + 3.0
FPC_HOLE_R = 4.4  # ribbon is ~6.3 wide, any rotation passes

# USB adapter "USB-test-MD50-V3.3", measured 44 × 37 × 1; features scaled from the photo
PCB_L, PCB_H, PCB_T = 44.0, 37.0, 1.0
HOLES = ((2.8, 2.5), (41.6, 2.7), (3.1, 34.7))  # (from left, from top): TL, TR, BL
USB_FROM_TOP, USB_W, USB_T, USB_LEN, USB_OVER = 10.3, 8.9, 3.2, 7.3, 0.4
J2_FROM_LEFT, J2_W, J2_H, J2_T = 18.8, 11.0, 5.3, 2.0

# Pod (sealed adapter bay)
CAV_X0 = -4.5
POST_H = 2.5
PCB_X0 = CAV_X0 + POST_H  # PCB back face, component side faces +X
CAV_Y0 = Y_FLOOR_BACK + 0.2
PCB_Y0 = CAV_Y0 + 0.5
CAV_Y1 = PCB_Y0 + PCB_L + USB_OVER + 0.3
PCB_Z0 = 2.0  # J2 sits just above the FPC hole
PCB_Z1 = PCB_Z0 + PCB_H
CAV_Z0, CAV_Z1 = -6.0, PCB_Z1 + 0.5
GROOVE_X0, GROOVE_X1, GROOVE_D = 6.0, 8.2, 1.2
POD_WALL = GROOVE_D + 1.8  # keeps >= 1.6 (FDM min unsupported wall) behind the groove
POD_X0, POD_X1 = CAV_X0 - POD_WALL, GROOVE_X1 + 1.6
POD_Y1 = CAV_Y1 + POD_WALL
POD_Z0, POD_Z1 = CAV_Z0 - POD_WALL, CAV_Z1 + 2.0
POST_R, PILOT_R = 2.8, 1.0  # M2.5 self-tapping screws; 1.8 mm post wall

# USB-C rear opening: tall and thin, sized for the cable overmold
USB_Z = PCB_Z1 - USB_FROM_TOP
USB_X = PCB_X0 + PCB_T + USB_T / 2
USB_HOLE_X, USB_HOLE_Z = 8.0, 14.0

# Lid: slides down the groove from the top, 1.5 proud for grip
LID_T = 2.0
LID_Y0, LID_Y1 = CAV_Y0 - GROOVE_D + 0.2, CAV_Y1 + GROOVE_D - 0.2
LID_Z0, LID_Z1 = CAV_Z0 - GROOVE_D + 0.2, POD_Z1 + 1.5

# Flat anti-tip base
BASE_TH = 4.0
BASE_FRONT, BASE_REAR = 8.0, 6.0
PLINTH_HALF_W = 28.0

_C, _S = math.cos(math.radians(TILT)), math.sin(math.radians(TILT))
TZ = BASE_TH + 1.0 + (Y_FLOOR_BACK * _S + R_CUP * _C)  # cup bottom 1 mm into the plinth
TY = BASE_FRONT - (Y_RIM * _C - R_CUP * _S)  # cup front edge at the base toe


def to_world(y, z):
    return (y * _C + z * _S + TY, -y * _S + z * _C + TZ)


def world():
    return bd.Pos(0, TY, TZ) * bd.Rot(-TILT, 0, 0)


def box(x0, x1, y0, y1, z0, z1):
    return bd.Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * bd.Box(
        x1 - x0, y1 - y0, z1 - z0
    )


def ycyl(r, y0, y1, x=0.0, z=0.0):
    return bd.Pos(x, (y0 + y1) / 2, z) * bd.Cylinder(r, y1 - y0, rotation=(-90, 0, 0))


def xcyl(r, x0, x1, y, z):
    return bd.Pos((x0 + x1) / 2, y, z) * bd.Cylinder(r, x1 - x0, rotation=(0, 90, 0))


def side_prism(pts, x0, x1):
    face = bd.Plane.YZ * bd.Polygon(*pts, align=None)
    return bd.Pos((x0 + x1) / 2, 0, 0) * bd.extrude(
        face, amount=(x1 - x0) / 2, both=True
    )


def hole_positions():
    return [(PCB_Y0 + hx, PCB_Z1 - hz) for hx, hz in HOLES]


@model
def stand():
    w = world()
    outer = ycyl(R_CUP, Y_RIM, Y_FLOOR_BACK) + box(
        POD_X0, POD_X1, Y_FLOOR_BACK - 0.4, POD_Y1, POD_Z0, POD_Z1
    )

    floor_z = BASE_TH - 0.5
    yf, zf = to_world(Y_RIM, -R_CUP + 8.0)
    yb, zb = to_world(Y_FLOOR_BACK, -R_CUP + 8.0)
    plinth = side_prism(
        [(yf, floor_z), (yf, zf), (yb, zb), (yb, floor_z)],
        -PLINTH_HALF_W,
        PLINTH_HALF_W,
    )
    sf, szf = to_world(20.0, POD_Z0 + 1.0)
    sb, szb = to_world(POD_Y1, POD_Z0 + 1.0)
    spine = side_prism(
        [(sf, floor_z), (sf, szf), (sb, szb), (sb, floor_z)], POD_X0, POD_X1
    )

    base_y1 = sb + BASE_REAR
    base = bd.Pos(0, base_y1 / 2, 0) * bd.extrude(
        bd.RectangleRounded(2 * (R_CUP + 5.0), base_y1, 8.0), BASE_TH
    )

    cuts = (
        ycyl(R_BORE, Y_RIM - 1.0, Y_FLOOR)
        + (
            ycyl(PEG_RO, Y_FLOOR - EPS, Y_FLOOR + PEG_SLOT)
            - ycyl(PEG_RI, Y_FLOOR - 1.0, Y_FLOOR + PEG_SLOT + 1.0)
        )
        + ycyl(FPC_HOLE_R, Y_FLOOR - EPS, CAV_Y0 + EPS)
        + box(CAV_X0, POD_X1 + 1.0, CAV_Y0, CAV_Y1, CAV_Z0, CAV_Z1)
        + box(
            GROOVE_X0,
            GROOVE_X1,
            CAV_Y0 - GROOVE_D,
            CAV_Y1 + GROOVE_D,
            CAV_Z0 - GROOVE_D,
            R_CUP + 8.0,
        )
        + box(
            USB_X - USB_HOLE_X / 2,
            USB_X + USB_HOLE_X / 2,
            CAV_Y1 - EPS,
            POD_Y1 + 1.0,
            USB_Z - USB_HOLE_Z / 2,
            USB_Z + USB_HOLE_Z / 2,
        )
    )
    posts = [xcyl(POST_R, CAV_X0 - 1.0, PCB_X0, y, z) for y, z in hole_positions()]
    pilots = [
        xcyl(PILOT_R, CAV_X0 - 1.5, PCB_X0 + EPS, y, z) for y, z in hole_positions()
    ]

    body = base + plinth + spine + w * outer
    body = body - w * cuts
    for post in posts:
        body = body + w * post
    for pilot in pilots:
        body = body - w * pilot

    bb = body.bounding_box()
    assert abs(bb.min.Z) < 1e-6, bb.min.Z
    body.label = "stand"
    body.color = COLOR
    return body


def lid_plate():
    return bd.Pos((LID_Y1 - LID_Y0) / 2, (LID_Z1 - LID_Z0) / 2, LID_T / 2) * bd.Box(
        LID_Y1 - LID_Y0, LID_Z1 - LID_Z0, LID_T
    )


@model
def lid():
    plate = lid_plate()  # printed flat
    plate.label = "lid"
    plate.color = COLOR
    return plate


@model
def fit_check():
    """Stand + lid in place with dummy display and adapter, to check fits."""
    w = world()
    s = stand().shape
    lid_shape = lid().shape
    lid_frame = bd.Location(
        bd.Plane(
            origin=(GROOVE_X0 + 0.1, LID_Y0, LID_Z0), x_dir=(0, 1, 0), z_dir=(1, 0, 0)
        )
    )
    placed_lid = w * lid_frame * lid_shape
    placed_lid.label = "lid"

    display = ycyl(DISPLAY_D / 2, Y_FLOOR - DISPLAY_DEPTH, Y_FLOOR - 9.0) + ycyl(
        17.0, Y_FLOOR - 9.0, Y_FLOOR
    )
    for ang in (200.0, 120.0):
        a = math.radians(ang)
        display = display + ycyl(
            1.5, Y_FLOOR - EPS, Y_FLOOR + 4.0, 10.0 * math.cos(a), 10.0 * math.sin(a)
        )
    display = w * display
    display.label = "display"
    display.color = "#2B2B2B"

    pcb = w * box(PCB_X0, PCB_X0 + PCB_T, PCB_Y0, PCB_Y0 + PCB_L, PCB_Z0, PCB_Z1)
    pcb.label = "adapter_pcb"
    pcb.color = "#2E8B3A"
    usb_y1 = PCB_Y0 + PCB_L + USB_OVER
    usb = w * box(
        PCB_X0 + PCB_T,
        PCB_X0 + PCB_T + USB_T,
        usb_y1 - USB_LEN,
        usb_y1,
        USB_Z - USB_W / 2,
        USB_Z + USB_W / 2,
    )
    usb.label = "usb_c"
    usb.color = "#C0C0C0"
    j2y = PCB_Y0 + J2_FROM_LEFT
    j2 = w * box(
        PCB_X0 + PCB_T,
        PCB_X0 + PCB_T + J2_T,
        j2y - J2_W / 2,
        j2y + J2_W / 2,
        PCB_Z0,
        PCB_Z0 + J2_H,
    )
    j2.label = "j2_fpc"
    j2.color = "#E8E0C8"

    return bd.Compound(
        children=[s, placed_lid, display, pcb, usb, j2], label="viewe_case"
    )


if __name__ == "__main__":
    stand()
    lid()
    fit_check()
