#include <Servo.h>

#define FLEX_PIN1 A0
#define FLEX_PIN2 A1
#define FLEX_PIN3 A2
#define FLEX_PIN4 A3

Servo servo;
int contadorL = 0;
int contadorR = 0;

float V_min_long = 3.00;
float V_max_long = 3.68;
float V_min_short = 1.77;
float V_max_short = 2.33;

int ANGULO_MIN = 0;
int ANGULO_MAX = 90;

float lastAngle[4] = {0, 0, 0, 0};

const float torqueServo = 1.8 * 0.098; // Torque en N·m (1.8 kg·cm a N·m)
const float radioServo = 0.02; // Radio de acción en metros (2 cm)

void setup() {
  Serial.begin(9600);
  servo.attach(9);
  servo.write(90); // posición neutra
  Serial.println("Ingresa L para girar a la izquierda, R para girar a la derecha o S para detener.");
}

void loop() {
  controlarServo();
  mostrarFlexisensores();
  delay(500);
}

void mostrarFlexisensores() {
  float voltage[4];
  float angle[4];

  voltage[0] = readFlex(FLEX_PIN1);
  voltage[1] = readFlex(FLEX_PIN2);
  voltage[2] = readFlex(FLEX_PIN3);
  voltage[3] = readFlex(FLEX_PIN4);

  angle[0] = convertToAngle(voltage[0], V_min_long, V_max_long);
  angle[1] = convertToAngle(voltage[1], V_min_long, V_max_long);
  angle[2] = convertToAngle(voltage[2], V_min_short, V_max_short);
  angle[3] = convertToAngle(voltage[3], V_min_short, V_max_short);

  for (int i = 0; i < 4; i++) {
    if (abs(angle[i] - lastAngle[i]) > 1) {
      Serial.print("Dedo ");
      switch (i) {
        case 0: Serial.print("índice"); break;
        case 1: Serial.print("medio"); break;
        case 2: Serial.print("anular"); break;
        case 3: Serial.print("meñique"); break;
      }
      Serial.print(" - Voltaje: ");
      Serial.print(voltage[i], 2);
      Serial.print(" V | Ángulo: ");
      Serial.print(angle[i]);
      Serial.println(" grados");
      
      float fuerza = calcularFuerzaFlex(angle[i]);
      Serial.print("Fuerza ejercida por el dedo: ");
      Serial.print(fuerza);
      Serial.println(" N");
      lastAngle[i] = angle[i];
    }
  }
}

void controlarServo() {
  if (Serial.available() > 0) {
    char comando = Serial.read();
    int velocidad;

    if (comando == 'S' || comando == 's') {
      servo.write(90);
      Serial.println("Motor detenido.");
    } 
    else if (comando == 'L' || comando == 'l') {
      velocidad = 67;
      servo.write(velocidad);
      Serial.print("Girando a la izquierda a velocidad: ");
      Serial.println(velocidad);
      Serial.print("Fuerza generada por el servo: ");
      Serial.print(calcularFuerzaServo(velocidad));
      Serial.println(" N");
      delay(3000);
      servo.write(90);
      Serial.println("Motor detenido.");
      contadorL++;
    } 
    else if (comando == 'R' || comando == 'r') {
      velocidad = 115;
      servo.write(velocidad);
      Serial.print("Girando a la derecha a velocidad: ");
      Serial.println(velocidad);
      Serial.print("Fuerza generada por el servo: ");
      Serial.print(calcularFuerzaServo(velocidad));
      Serial.println(" N");
      delay(3000);
      servo.write(90);
      Serial.println("Motor detenido.");
      contadorR++;
    } 
    else {
      Serial.println("Comando inválido. Usa L, R o S.");
    }
  }
}

float readFlex(int pin) {
  float voltage = 0;
  int n = 20;
  for (int i = 0; i < n; i++) {
    voltage += analogRead(pin) * (5.0 / 1023.0);
  }
  voltage /= n;
  return voltage;
}

float convertToAngle(float voltage, float vMin, float vMax) {
  float angle = map(voltage * 100, vMin * 100, vMax * 100, ANGULO_MIN, ANGULO_MAX);
  return constrain(angle, ANGULO_MIN, ANGULO_MAX);
}

float calcularFuerzaFlex(float angulo) {
  return angulo * 0.05; // Factor experimental
}

float calcularFuerzaServo(int velocidad) {
  return torqueServo / radioServo;
}
