
#include "Arduino.h"
#include "Wire.h"
#include <Adafruit_NeoPixel.h>

//define DEBUG //Uncoment this line to get debug information of the Serial port.

#ifdef DEBUG
 #define DEBUG_PRINT(x)     Serial.print (x)
 #define DEBUG_PRINTDEC(x)     Serial.print (x, DEC)
 #define DEBUG_PRINTBIN(x)     Serial.print (x, BIN)
 #define DEBUG_PRINTLN(x)  Serial.println (x)
 #define DEBUG_WRITE(x)     Serial.write (x)
 #define DEBUG_WRITE_LEN(x,len)     Serial.write (x,len)
#else
 #define DEBUG_PRINT(x)
 #define DEBUG_PRINTDEC(x)
 #define DEBUG_PRINTBIN(x)
 #define DEBUG_PRINTLN(x)
 #define DEBUG_WRITE(x)
 #define DEBUG_WRITE_LEN(x,len)
#endif

#define LED_TYPE  NEO_GRB + NEO_KHZ800
#define I2CADDRESS 0x04

Adafruit_NeoPixel strip = Adafruit_NeoPixel();

bool gotData = false;
int command = 0;
int neopixelPin = 0;
int neopixelLeds = 0;
int neopixelBrightness = 0;
int redValue = 0;
int greenValue = 0;
int blueValue = 0;

void receiveEvent(int byteCount){
    DEBUG_PRINT("WIRE BUFFER: ");
    DEBUG_PRINTLN(Wire.available());
    DEBUG_PRINT("CMD ");
    command = Wire.read();
    DEBUG_PRINTLN(command);

    DEBUG_PRINT("PIN ");
    neopixelPin = Wire.read();
    DEBUG_PRINTLN(neopixelPin);

    DEBUG_PRINT("N LED ");
    neopixelLeds = Wire.read();
    DEBUG_PRINTLN(neopixelLeds);

    DEBUG_PRINT("BRIGHTNESS ");
    neopixelBrightness = Wire.read();
    DEBUG_PRINTLN(neopixelBrightness);

    DEBUG_PRINT("RED ");
    redValue = Wire.read();
    DEBUG_PRINTLN(redValue);

    DEBUG_PRINT("GREEN ");
    greenValue = Wire.read();
    DEBUG_PRINTLN(greenValue);

    DEBUG_PRINT("BLUE ");
    blueValue = Wire.read();
    DEBUG_PRINTLN(blueValue);

    gotData = true;

}

void setup() {

	Wire.begin(I2CADDRESS);
	#ifdef DEBUG
    Serial.begin(115200);
    while (!Serial) ;
    Serial.println("Debuging...");
	#endif
  Wire.onReceive(receiveEvent);
}

void loop() {

  if(gotData){
    strip.setPin(neopixelPin);
    strip.setBrightness(neopixelBrightness);
    strip.updateLength(neopixelLeds);
    strip.updateType(LED_TYPE);
    strip.begin();
    for(uint16_t i=0; i<strip.numPixels(); i++) {
      strip.setPixelColor(i, strip.Color(redValue, greenValue, blueValue));
    }
    strip.show();
    gotData = false;
  }

}
