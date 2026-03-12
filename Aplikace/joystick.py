"""
Pygame ovladac pro dve servo osy (X, Y) a laser pripojene k Arduinu.
Komunikace pres USB seriovou linku @ 115200 baudu.

Rezimy:
  MANUAL  - serva rizena mysi, laser prepinan mezernikem
  IDLE    - autonomni skenovani sinusovymi vlnami, laser vypnut

Prepinani rezimu: klavesa TAB nebo kliknuti na tlacitko v okne

Zavislosti:
    pip install pygame pyserial

Pouziti:
    po spusteni automaticky vyber nebo interaktivni menu pro vyber portu
"""

import sys
import math
import time
import pygame
import serial
import serial.tools.list_ports
from enum import Enum, auto

# ─────────────────────────────────────────────
#  Konfigurace
# ─────────────────────────────────────────────
WINDOW_W = 600       # sirka okna [px]
WINDOW_H = 600       # vyska okna [px]
BAUD_RATE = 115200    # rychlost seriove linky
LOOP_FPS = 60        # max. snimku za sekundu hlavni smycky
RECONNECT_DELAY = 3.0       # sekund mezi pokusy o znovupripojeni

# Omezeni rozsahu osy Y - mechanika nepotrebuje plnych 180°
SERVO_Y_MIN = 50        # minimalni uhel osy Y [°]
SERVO_Y_MAX = 130       # maximalni uhel osy Y [°]

# Idle skenovani - frekvence oscilaci [Hz]
#   X - rychlejsi "zametani" zleva doprava (perioda ~5.5 s)
#   Y - pomalejsi, jemnejsi zdvih        (perioda ~14 s)
IDLE_FREQ_X = 0.18
IDLE_FREQ_Y = 0.07

# Barvy (R, G, B)
COLOR_BG = (18,  18,  18)
COLOR_GRID = (40,  40,  40)
COLOR_CENTER = (55,  55,  55)    # pevny kriz stredu
COLOR_DOT_OFF = (0,  160, 255)    # manual kurzor, laser vypnut
COLOR_DOT_ON = (255,  60,  60)   # manual kurzor, laser zapnut
COLOR_IDLE_DOT = (255, 165,   0)   # idle kurzor (oranzova)
COLOR_TEXT = (200, 200, 200)
COLOR_WARN = (255, 200,   0)
COLOR_OK = (0,  210, 100)
COLOR_MODE_MAN = (0,  210, 100)    # zelena - MANUAL
COLOR_MODE_IDLE = (255, 165,   0)   # oranzova - IDLE
COLOR_BTN_BG = (45,  45,  45)
COLOR_BTN_HOV = (70,  70,  70)
COLOR_BTN_BDR = (100, 100, 100)


# ─────────────────────────────────────────────
#  Stavovy automat
# ─────────────────────────────────────────────
class Mode(Enum):
    MANUAL = auto()
    IDLE   = auto()


# ─────────────────────────────────────────────
#  Hledani a vyber serioveho portu
# ─────────────────────────────────────────────

# Klicova slova, jejichz pritomnost v nazvu/popisu portu znamena,
# ze port preskocime (Bluetooth / bezdratove adaptery).
_BT_BLACKLIST = ("bluetooth", "bth", "wireless")


def _is_bluetooth(port_info) -> bool:
    """Vrati True, pokud port vypada jako Bluetooth / bezdratovy."""
    haystack = " ".join([
        port_info.device      or "",
        port_info.name        or "",
        port_info.description or "",
    ]).lower()
    return any(kw in haystack for kw in _BT_BLACKLIST)


def find_serial_ports() -> list:
    """
    Vrati seznam portu (ListPortInfo), ktere nejsou Bluetooth / bezdratove.
    Razeni: USB porty (usbmodem, usbserial, ttyACM, ttyUSB) prednostne,
    zbytek (COM, ...) na konec.
    """
    usb_kw = ("usbmodem", "usbserial", "ttyacm", "ttyusb")
    usb_ports   = []
    other_ports = []

    for p in serial.tools.list_ports.comports():
        if _is_bluetooth(p):
            continue
        if any(kw in p.device.lower() for kw in usb_kw):
            usb_ports.append(p)
        else:
            other_ports.append(p)

    return usb_ports + other_ports


def select_port() -> str:
    """
    Interaktivni vyber serioveho portu pred spustenim Pygame.

    - 0 portu  -> vypise chybu a ukonci program (sys.exit)
    - 1 port   -> pouzije ho automaticky
    - 2+ portu -> zobrazi cislovane menu, ceka na volbu uzivatele
    """
    ports = find_serial_ports()

    if len(ports) == 0:
        print("\n[CHYBA] Nebyl nalezen zadny seriovy port (krome Bluetooth).")
        print("        Zkontrolujte, zda je Arduino pripojeno pres USB.")
        sys.exit(1)

    if len(ports) == 1:
        p = ports[0]
        print(f"[Serial] Automaticky zvolen port: {p.device}  ({p.description})")
        return p.device

    # Vice portu - interaktivni menu
    print("\n[Serial] Nalezeno vice portu. Vyberte, ktery chcete pouzit:\n")
    for i, p in enumerate(ports, start=1):
        print(f"  [{i}] {p.device:<25}  {p.description}")
    print()

    while True:
        try:
            choice = input(f"Zadejte cislo portu (1-{len(ports)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(ports):
                selected = ports[idx]
                print(f"[Serial] Zvolen port: {selected.device}  ({selected.description})\n")
                return selected.device
            else:
                print(f"  Neplatna volba. Zadejte cislo od 1 do {len(ports)}.")
        except (ValueError, EOFError):
            print("  Neplatny vstup. Zadejte cele cislo.")


# ─────────────────────────────────────────────
#  Mapovani souradnic <-> uhly servo
# ─────────────────────────────────────────────
def map_range(value: float,
              in_min: float, in_max: float,
              out_min: float, out_max: float) -> int:
    """Linearne premapuje hodnotu z jednoho rozsahu do druheho a zaokrouhli na int."""
    if in_max == in_min:
        return int(out_min)
    ratio  = (value - in_min) / (in_max - in_min)
    result = out_min + ratio * (out_max - out_min)
    # Clamping - pojistka proti out-of-range hodnotam
    return int(max(min(out_min, out_max), min(max(out_min, out_max), result)))


def angle_to_pixel_x(angle: int) -> int:
    """Prevede uhel osy X (0-180°) na pixel X v okne."""
    return map_range(angle, 180, 0, 0, WINDOW_W - 1)


def angle_to_pixel_y(angle: int) -> int:
    """Prevede uhel osy Y (SERVO_Y_MIN-SERVO_Y_MAX) na pixel Y v okne (invertovano)."""
    return map_range(angle, SERVO_Y_MAX, SERVO_Y_MIN, 0, WINDOW_H - 1)


# ─────────────────────────────────────────────
#  Idle - vypocet autonomnich uhlu
# ─────────────────────────────────────────────
def compute_idle_angles(t: float) -> tuple[int, int]:
    """
    Osa X: sin() -> plynule kyvani pres celych 0-180°
    Osa Y: cos() s nizsi frekvenci -> pomalejsi oscilace v povolenem rozsahu
    Ruzne frekvence a funkce zajistuji, ze pohyb nevypada jako jednoducha smycka .
    """
    raw_x  = 90.0 + 90.0 * math.sin(2 * math.pi * IDLE_FREQ_X * t)

    mid_y  = (SERVO_Y_MIN + SERVO_Y_MAX) / 2.0
    half_y = (SERVO_Y_MAX - SERVO_Y_MIN) / 2.0
    raw_y  = mid_y + half_y * math.cos(2 * math.pi * IDLE_FREQ_Y * t)

    angle_x = int(max(0, min(180, round(raw_x))))
    angle_y = int(max(SERVO_Y_MIN, min(SERVO_Y_MAX, round(raw_y))))
    return angle_x, angle_y


# ─────────────────────────────────────────────
#  Vykreslovani HUD
# ─────────────────────────────────────────────
def draw_ui(surface: pygame.Surface,
            font_large: pygame.font.Font,
            font_small: pygame.font.Font,
            font_mode:  pygame.font.Font,
            mx: int, my: int,
            angle_x: int, angle_y: int,
            laser_on: bool,
            serial_ok: bool,
            mode: Mode,
            btn_rect: pygame.Rect,
            mouse_pos: tuple[int, int]) -> None:
    """Vykresli mrizku, kriz, kurzorovy bod, HUD a tlacitko prepinani rezimu."""

    surface.fill(COLOR_BG)

    # -- Mrizka --
    step = WINDOW_W // 6
    for i in range(0, WINDOW_W + 1, step):
        pygame.draw.line(surface, COLOR_GRID, (i, 0), (i, WINDOW_H))
        pygame.draw.line(surface, COLOR_GRID, (0, i), (WINDOW_W, i))

    # -- Pevny kriz stredu okna --
    cx, cy = WINDOW_W // 2, WINDOW_H // 2
    pygame.draw.line(surface, COLOR_CENTER, (0, cy), (WINDOW_W, cy), 1)
    pygame.draw.line(surface, COLOR_CENTER, (cx, 0), (cx, WINDOW_H), 1)

    # -- Pohyblivy kurzor (odpovida aktualnim uhlum servo) --
    # V IDLE rezimu pouzijeme odlisnou barvu a teckovany styl krize,
    # aby bylo vizualne jasne, ze mys ted nema kontrolu.
    if mode == Mode.MANUAL:
        dot_color = COLOR_DOT_ON if laser_on else COLOR_DOT_OFF
        arm_len, thickness = 15, 2
    else:
        dot_color = COLOR_IDLE_DOT
        arm_len, thickness = 12, 2

    pygame.draw.line(surface, dot_color, (mx - arm_len, my), (mx + arm_len, my), thickness)
    pygame.draw.line(surface, dot_color, (mx, my - arm_len), (mx, my + arm_len), thickness)
    pygame.draw.circle(surface, dot_color, (mx, my), 8, 2)

    # V IDLE pridame vnejsi krouzek jako dalsi vizualni cue
    if mode == Mode.IDLE:
        pygame.draw.circle(surface, dot_color, (mx, my), 16, 1)

    # -- Textovy HUD (levy horni roh) --
    pad    = 12
    line_h = 26
    y_off  = pad

    # Stav pripojeni
    conn_color = COLOR_OK if serial_ok else COLOR_WARN
    conn_text  = "● PRIPOJENO" if serial_ok else "○ ODPOJENO - hledam port..."
    surface.blit(font_small.render(conn_text, True, conn_color), (pad, y_off))
    y_off += line_h + 2

    # Aktualni rezim - vyrazne
    mode_label = "MODE: MANUAL" if mode == Mode.MANUAL else "MODE: IDLE"
    mode_color = COLOR_MODE_MAN  if mode == Mode.MANUAL else COLOR_MODE_IDLE
    surface.blit(font_mode.render(mode_label, True, mode_color), (pad, y_off))
    y_off += line_h + 6

    # Uhly a laser
    hud_lines = [
        (f"Servo X : {angle_x:>3}°", COLOR_TEXT),
        (f"Servo Y : {angle_y:>3}°", COLOR_TEXT),
        (f"Laser   : {'ZAP ●' if laser_on else 'VYP ○'}",
         COLOR_DOT_ON if laser_on else COLOR_TEXT),
    ]
    for txt, col in hud_lines:
        surface.blit(font_large.render(txt, True, col), (pad, y_off))
        y_off += line_h

    # -- Tlacitko prepinani rezimu (pravy horni roh) --
    hovered   = btn_rect.collidepoint(mouse_pos)
    btn_bg    = COLOR_BTN_HOV if hovered else COLOR_BTN_BG
    btn_label = "-> IDLE"   if mode == Mode.MANUAL else "-> MANUAL"
    btn_color = COLOR_MODE_IDLE if mode == Mode.MANUAL else COLOR_MODE_MAN

    pygame.draw.rect(surface, btn_bg,        btn_rect, border_radius=6)
    pygame.draw.rect(surface, COLOR_BTN_BDR, btn_rect, 1, border_radius=6)
    btn_surf = font_small.render(btn_label, True, btn_color)
    bx = btn_rect.x + (btn_rect.w - btn_surf.get_width())  // 2
    by = btn_rect.y + (btn_rect.h - btn_surf.get_height()) // 2
    surface.blit(btn_surf, (bx, by))

    # -- Napoveda (dolni okraj) --
    if mode == Mode.MANUAL:
        hint = "Pohyb mysi = servo  |  Mezernik = laser  |  TAB = IDLE  |  ESC = konec"
    else:
        hint = "Autonomni skenovani  |  TAB = MANUAL  |  ESC = konec"
    surface.blit(font_small.render(hint, True, (75, 75, 75)),
                 (pad, WINDOW_H - pad - 18))


# ─────────────────────────────────────────────
#  Hlavni smycka
# ─────────────────────────────────────────────
def main(port: str) -> None:
    pygame.init()
    pygame.display.set_caption("Arduino Servo & Laser Controller")
    screen  = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    clock   = pygame.time.Clock()
    font_l  = pygame.font.SysFont("monospace", 22, bold=True)
    font_s  = pygame.font.SysFont("monospace", 14)
    font_m  = pygame.font.SysFont("monospace", 18, bold=True)   # MODE napis

    # Tlacitko prepinani (pravy horni roh)
    btn_rect = pygame.Rect(WINDOW_W - 130, 10, 120, 32)

    # Vychozi pozice kurzoru = stred okna -> serva startuji na 90° bez skubnuti
    pygame.mouse.set_pos(WINDOW_W // 2, WINDOW_H // 2)

    # -- Stav aplikace --
    mode         = Mode.MANUAL
    laser_on     = False
    last_angle_x = -1       # "sentinel" - vynuti prvni odeslani po pripojeni
    last_angle_y = -1
    last_laser   = -1

    ser: serial.Serial | None = None
    last_reconnect = 0.0

    # -- Pomocne funkce (closure pres promenne vyse) --

    def try_connect() -> serial.Serial | None:
        """Pokusi se otevrit seriovy port predany pri spusteni. Vrati objekt nebo None."""
        try:
            s = serial.Serial(port, BAUD_RATE, timeout=0.1)
            time.sleep(2.0)          # cekame na reset Arduina po otevreni portu
            s.reset_input_buffer()
            print(f"[Serial] Otevren port {port} @ {BAUD_RATE} baud.")
            return s
        except serial.SerialException as e:
            print(f"[Serial] Chyba pri otevirani {port}: {e}")
            return None

    def send(s: serial.Serial, ax: int, ay: int, lz: int) -> bool:
        """Sestavi a odesle paket. Vrati False pri chybe."""
        msg = f"X{ax}:Y{ay}:L{lz}\n"
        try:
            s.write(msg.encode("ascii"))
            return True
        except (serial.SerialException, OSError) as e:
            print(f"[Serial] Chyba pri odesilani: {e}")
            return False

    def switch_to(new_mode: Mode, cur_ax: int, cur_ay: int) -> Mode:
        """
        Prepne stavovy automat do noveho rezimu.

        IDLE -> MANUAL:
          Presune kurzor mysi na pixel odpovidajici poslednim uhlum servo.
          Tim zajistime, ze serva pri predani kontroly neskubnou na jinou polohu.

        MANUAL -> IDLE:
          Vypne laser (v Idle je laser vzdy off).
        """
        nonlocal laser_on
        if new_mode == Mode.MANUAL:
            px = angle_to_pixel_x(cur_ax)
            py = angle_to_pixel_y(cur_ay)
            pygame.mouse.set_pos(px, py)
            print(f"[Mode] -> MANUAL  (kurzor -> pixel {px},{py}  =  {cur_ax}°, {cur_ay}°)")
        else:
            laser_on = False
            print("[Mode] -> IDLE")
        return new_mode

    # -- Smycka udalosti --
    running = True
    while running:

        now_t = time.time()     # timestamp pro sin/cos v Idle

        # Zpracovani udalosti pygame
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE and mode == Mode.MANUAL:
                    # Mezernik prepina laser pouze v MANUAL rezimu
                    laser_on = not laser_on
                elif event.key == pygame.K_TAB:
                    new  = Mode.IDLE if mode == Mode.MANUAL else Mode.MANUAL
                    mode = switch_to(new, last_angle_x, last_angle_y)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and btn_rect.collidepoint(event.pos):
                    new  = Mode.IDLE if mode == Mode.MANUAL else Mode.MANUAL
                    mode = switch_to(new, last_angle_x, last_angle_y)

        # -- Vypocet cilovych uhlu podle aktivniho rezimu --
        if mode == Mode.MANUAL:
            # Mys ridi serva
            raw_mx, raw_my = pygame.mouse.get_pos()
            mx = max(0, min(WINDOW_W - 1, raw_mx))
            my = max(0, min(WINDOW_H - 1, raw_my))

            angle_x   = map_range(mx, 0, WINDOW_W - 1, 180, 0)
            angle_y   = map_range(my, 0, WINDOW_H - 1, SERVO_Y_MAX, SERVO_Y_MIN)
            laser_int = 1 if laser_on else 0

        else:  # IDLE - autonomni skenovani
            angle_x, angle_y = compute_idle_angles(now_t)
            laser_int = 0       # laser vzdy vypnut v IDLE

            # Virtualni pixel pro vykresleni kurzoru odpovida uhlu servo
            mx = angle_to_pixel_x(angle_x)
            my = angle_to_pixel_y(angle_y)

        # -- Reconnect --
        if ser is None or not ser.is_open:
            now_mono = time.monotonic()
            if now_mono - last_reconnect >= RECONNECT_DELAY:
                last_reconnect = now_mono
                ser = try_connect()
                if ser:
                    last_angle_x = last_angle_y = last_laser = -1

        # -- Odeslani dat pouze pri zmene (throttling) --
        if ser and ser.is_open:
            if (angle_x   != last_angle_x or
                    angle_y   != last_angle_y or
                    laser_int != last_laser):
                ok = send(ser, angle_x, angle_y, laser_int)
                if ok:
                    last_angle_x = angle_x
                    last_angle_y = angle_y
                    last_laser   = laser_int
                else:
                    # Chyba -> zavreme port, pristi iterace zkusi reconnect
                    try:
                        ser.close()
                    except Exception:
                        pass
                    ser = None

        # -- Vykresleni --
        serial_ok = ser is not None and ser.is_open
        draw_ui(screen, font_l, font_s, font_m,
                mx, my, angle_x, angle_y,
                laser_on, serial_ok, mode,
                btn_rect, pygame.mouse.get_pos())
        pygame.display.flip()

        clock.tick(LOOP_FPS)

    # -- Cleanup: --
    if ser and ser.is_open:
        try:
            print("[App] Odesilam homing prikaz (X90:Y90:L0)...")
            ser.write(b"X90:Y90:L0\n")
            time.sleep(0.5)   # Arduino musi stihnout prijmout a provest prikaz
            ser.close()
        except Exception:
            pass
    pygame.quit()
    print("[App] Ukonceno.")


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Interaktivni vyber portu probehne PRED inicializaci Pygame,
    # aby pripadna chybova hlaseni nebo menu bylo videt v terminalu.
    chosen_port = select_port()
    main(port=chosen_port)