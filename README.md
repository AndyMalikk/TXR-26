# TXR-26: Automatizovaná laserová věž (Arduino)

Tento repozitář obsahuje zdrojové kódy pro ročníkovou práci **TXR-26 Laserová věž**. Systém je postaven na platformě Arduino Uno, využívá díly vytištěné na 3D tiskárně a je řízen servomotory ve dvou osách (X/Y).

## 📂 Soubory a složky

* **`Manual_Script`**: Složka obsahující kód pro manuální režim. Umožňuje přesné ovládání věže pomocí joysticku a zahrnuje funkci přepínání (toggle) laseru.
* **`Idle_Script`**: Složka s kódem pro automatický režim. Věž v tomto módu samostatně skenuje prostor (simulace režimu "Sentry").

## 🛠️ Použitý Hardware

* **Řídicí jednotka:** Arduino Uno R3
* **Pohon:** Servomotory MG995 (Osa X - otáčení) a MG90 (Osa Y - náklon)
* **Ovládání:** Analogový Joystick KY-023
* **Napájení:** 4x AA Baterie (pro motory) + USB kabel (pro Arduino)

## 🚀 Jak kód nahrát

1.  Otevřete požadovaný soubor `.ino` v prostředí Arduino IDE.
2.  Připojte Arduino Uno k počítači pomocí USB.
3.  V menu vyberte správnou desku (**Tools -> Board -> Arduino Uno**) a port.
4.  Klikněte na tlačítko **Upload**.

---
*Vypracoval: Ondřej Malík, Třída 4ITA (Školní rok 2025/2026)*
