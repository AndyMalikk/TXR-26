# TXR-26: Interaktivní Pan-Tilt Věž (Arduino & Python)

Tento repozitář obsahuje zdrojové kódy a zkompilovaný software pro ročníkovou práci **TXR-26**. Jde o pohyblivou věž (Pan-Tilt systém) postavenou na platformě Arduino Uno s 3D tištěnými díly. Systém je plně řízen z počítače pomocí interaktivní aplikace napsané v jazyce Python.

### 📂 Soubory a složky

* **`Aplikace/dist/`**: Obsahuje zkompilovanou desktopovou aplikaci `joystick.exe` pro Windows. Tato aplikace tvoří hlavní uživatelské rozhraní a nevyžaduje instalaci jazyka Python.
* **`Aplikace/`**: Zdrojové kódy Python aplikace (`joystick.py`), které zajišťují čtení kurzoru, vykreslení UI a sériovou komunikaci s Arduinem.
* **Zdrojový kód pro Arduino**: Univerzální firmware pro Arduino Uno, který přijímá data z PC a ovládá servomotory i laser. (Již není potřeba přeflashovávat desku pro změnu režimů).

### 🛠️ Použitý Hardware

* **Řídicí jednotka:** Arduino Uno R3
* **Pohon:** Servomotory (Osa X pro horizontální otáčení, Osa Y pro vertikální náklon)
* **Užitečné zatížení (Payload):** Zaměřovací laserový modul (a maketa modulu ESP32-CAM pro demonstraci zapojení)
* **Napájení:** Externí blok 4× AA baterií (6 V) vyhrazený pro bezpečný chod servomotorů + USB kabel pro napájení a komunikaci Arduina s PC.

### 🚀 Jak systém spustit a ovládat

Firmware je v mikrokontroléru již nahrán, pro běžný provoz **není potřeba používat Arduino IDE**.

1. **Zapojení:** Připojte napájení servomotorů (baterie) a propojte Arduino s počítačem pomocí USB kabelu.
2. **Spuštění:** Ve složce `Aplikace/dist/` spusťte soubor **`joystick.exe`**.
3. **Ovládání aplikace:**
   * **Pohyb (Manuální režim):** Věž automaticky a plynule sleduje pohyb vašeho kurzoru myši/touchpadu po obrazovce.
   * **Laser:** Zapíná a vypíná se stisknutím klávesy **Mezerník (Space)**.
   * **Změna režimu:** Stisknutím klávesy **Tab** (nebo kliknutím na tlačítko v aplikaci) lze věž přepnout do **Idle režimu (Autopilot)**, ve kterém věž nezávisle na uživateli sama skenuje prostor. Opětovným stiskem se vrátíte do manuálního řízení.
