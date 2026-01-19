#include <Servo.h>

// servo X
Servo servoX;
const int pinJoyX = A1;
const int pinServoX = 11;
int positionX = 90;  //default pozice serva

// servo Y
Servo servoY;
const int pinJoyY = A0;
const int pinServoY = 10;
int positionY = 90;

int step = 1;  // kolik stupnu se hybe servo
int dt = 15;

// laser
const int laserJoySWPin = 12;
const int laserPin = 13;
bool laserIsOn = false;
int previousLaserState = HIGH;

void setup() {
  // put your setup code here, to run once:

  // servo X
  servoX.attach(pinServoX); //prirazeni pinu
  servoX.write(positionX);  // nastaveni pozice
  // servo Y
  servoY.attach(pinServoY);
  servoY.write(positionY);
  // laser
  pinMode(laserJoySWPin, INPUT_PULLUP);
  pinMode(laserPin, OUTPUT);
  digitalWrite(laserPin, LOW);

  Serial.begin(9600);
}

void loop() {
  // put your main code here, to run repeatedly:
  int valueX = analogRead(pinJoyX);  // cte hodnotu pozice joysticku
  int valueY = analogRead(pinJoyY);
  int currentLaserState = digitalRead(laserJoySWPin);

  // SERVO X
  // Pohyb DOPRAVA
  if (valueX < 400) {  // joystick ma hodnotu pwm 0-1024. Pod 400 je joystick vlevo
    positionX = positionX + step;
  }
  // pohyb DOLEVA
  if (valueX > 600) {
    positionX = positionX - step;
  }

  // SERVO Y
  // pohyb NAHORU
  if (valueY < 400) {  // joystick ma hodnotu pwm 0-1024. Pod 512 je joystick vlevo
    positionY = positionY + step;
  }
  // pohyb DOLU
  if (valueY > 600) {
    positionY = positionY - step;
  }

  //Limit pro servo
  positionX = constrain(positionX, 0, 180);
  positionY = constrain(positionY, 50, 130);

  servoX.write(positionX);
  servoY.write(positionY);
  delay(dt);

  // LASER
  // zjisteni zmacknuti tlacitka
  if (previousLaserState == HIGH && currentLaserState == LOW) {  //pokud bylo tlacitko nahore, a ted je dole, znamena ze bylo zmacknuto
    laserIsOn = !laserIsOn; //prohodi stav

    //zapsani stavu laseru
    if(laserIsOn){
      digitalWrite(laserPin, HIGH);
      Serial.println("Laser: zapnuty");
    } else{
      digitalWrite(laserPin, LOW);
      Serial.println("Laser: vypnuty");
    }

    //pojistni delay (aby se laser nevypl a ihned nezapl)
    delay(150);
  }
  previousLaserState = currentLaserState;
}
