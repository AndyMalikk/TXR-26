#include <Servo.h>


//  Nastaveni pinu a promennych

static const uint8_t PIN_SERVO_X = 11;
static const uint8_t PIN_SERVO_Y = 10;
static const uint8_t PIN_LASER = 12;


static const uint32_t BAUD_RATE = 115200;
static const uint8_t BUFFER_SIZE = 32;  // X000:Y000:L0\n = 14 znaku, rezerva 2x

Servo servoX;
Servo servoY;

// Prijimaci buffer pro neblokujici cteni
char rxBuffer[BUFFER_SIZE];
uint8_t rxIndex = 0;

// ---------------------------------------------
//  Pomocne funkce
// ---------------------------------------------

/**
 * Zpracuje kompletni radek ulozeny v rxBuffer.
 * Format: X{a}:Y{b}:L{c}
 * Pri chybe parsovani se nic neprovede (ochrana pred sumem na lince).
 */
void processLine(const char* line) {
  int angleX = -1, angleY = -1, laserState = -1;

  // sscanf bezpecne extrahuje cisla ze strukturovaneho retezce
  int parsed = sscanf(line, "X%d:Y%d:L%d", &angleX, &angleY, &laserState);

  if (parsed != 3) {
    // Neplatny format - ignorujeme a volitelne logujeme pro ladeni
    // Serial.print("[ERR] Bad packet: "); Serial.println(line);
    return;
  }

  // Constrain - pojistka proti neplatnym hodnotam (nikdy nezapiseme mimo rozsah)
  angleX = constrain(angleX, 0, 180);
  angleY = constrain(angleY, 0, 180);
  laserState = constrain(laserState, 0, 1);

  servoX.write(angleX);
  servoY.write(angleY);
  digitalWrite(PIN_LASER, laserState == 1 ? HIGH : LOW);
}

void setup() {
  // Inicializace seriove komunikace
  Serial.begin(BAUD_RATE);

  // piny
  pinMode(PIN_LASER, OUTPUT);
  digitalWrite(PIN_LASER, LOW);  // Laser vychozi stav = vypnuto

  // Pripojeni serv a nastaveni do stredove polohy (90 stupnu)
  servoX.attach(PIN_SERVO_X);
  servoY.attach(PIN_SERVO_Y);
  servoX.write(90);
  servoY.write(90);

  // Potvrzeni startu (viditelne v Serial Monitoru pro ladeni)
  Serial.println("[READY] Servo & Laser controller initialized.");
}

void loop() {
  /*
   * Cteme bajty ze serioveho bufferu jeden po druhem.
   * Az narazime na '\n', zpracujeme kompletni radek.
   * Tim zajistime, ze servomechanismy jsou obsluhovany bez preruseni.
   */
  while (Serial.available() > 0) {
    char incoming = (char)Serial.read();

    if (incoming == '\n' || incoming == '\r') {
      // Konec radku -> zpracovani (pokud buffer neni prazdny)
      if (rxIndex > 0) {
        rxBuffer[rxIndex] = '\0';  // Null-terminate
        processLine(rxBuffer);
        rxIndex = 0;  // Reset bufferu pro dalsi paket
      }
    } else {
      // Ukladame znak do bufferu s ochranou preteceni
      if (rxIndex < BUFFER_SIZE - 1) {
        rxBuffer[rxIndex++] = incoming;
      } else {
        // Buffer overflow -> zahazujeme poskozeny paket a resetujeme
        rxIndex = 0;
        // Serial.println("[ERR] Buffer overflow, packet discarded.");
      }
    }
  }
}
