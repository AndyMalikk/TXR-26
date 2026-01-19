#include <Servo.h>

//servo X
Servo servoX;
const int pinServoX = 11;
const int max_x = 179; //max uhel
const int min_x = 0; //min uhel
int positionX = 90; //default pozice
int directionX = 1; //1 - doprava, -1 - doleva
unsigned long previousTimeX = 0; //kolikrat se za 1 ms pohne servo o 1 stupen
int speedX = 30; //pohne se kazdych 30ms

//servo Y
Servo servoY;
const int pinServoY = 10;
const int max_y = 120;
const int min_y = 80;
int positionY = 90;
int directionY = 1; //1 - nahoru, -1 - dolu
unsigned long previousTimeY = 0; //unsigned long protoze int je moc mala hodnota
int speedY = 60; //pohne se kazdych 60ms



void setup() {
  //servo X
  servoX.attach(pinServoX); //priradim pin serva
  servoX.write(positionX); //zapisu pozici serva
  //servo Y
  servoY.attach(pinServoY);
  servoY.write(positionY);
}

void loop() {
  unsigned long currentTime = millis();

  //osa x - doleva/doprava
  if(currentTime - previousTimeX >= speedX){
    previousTimeX = currentTime; //reset stopek

    positionX = positionX + directionX; //pohnu o stupen (1 / -1)
    
    //limit
    if(positionX >= max_x){
      directionX = -1; //limit vpravo, otacim smer doleva
    }
    if(positionX <= min_x){
      directionX = 1; //limit vlevo, otacim smer doprava
    }

    servoX.write(positionX);
  }

  //osa Y - nahoru/dolu
  if(currentTime - previousTimeY >= speedY){
    previousTimeY = currentTime; //reset stopek

    positionY = positionY + directionY; //pohnu o stupen (1 / -1)
    
    //limit
    if(positionY >= max_y){
      directionY = -1; //limit nahore, otacim dolu
    }
    if(positionY <= min_y){
      directionY = 1; //limit dole, otacim nahoru
    }

    servoY.write(positionY);
  }
}