#include <ArduinoWebsockets.h>
#include <ESPAsyncWebServer.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <esp32cam.h>

#include "index.h"


#define A1 14
#define A5 15

#define PIR 13

#define LED 12

#define defaultInterval 10

const char* ssid = "YOLO32-CAM";
const char* pswd = "YOLOV4-2024";

// const char* def_ssid = "CEO";
// const char* def_pswd = "AA0E5BBD";

// const char* def_ssid = "MC";
// const char* def_pswd = "12345679";

char sta_ssid[32] = "MMERICHUKWU";
char sta_pswd[32] = "12345679";

const char* ws_server = "http://134.122.88.128:3001";

AsyncWebServer server(80);

char inp[90], resp[25], memo[25];

unsigned long t_stablink = 0, t_reconnect = 0;

static auto loRes = esp32cam::Resolution::find(320, 240);
static auto midRes = esp32cam::Resolution::find(350, 530);
static auto hiRes = esp32cam::Resolution::find(800, 600);
static auto HiRes = esp32cam::Resolution::find(1280, 1024);

unsigned long diff = 0, lastMillis = 0, last_plug_millis = 0, last_frame_millis = 0;

unsigned int interval = defaultInterval;

bool dark = false, s_stablink = false, client_connected = false;

using namespace websockets;

void onMessageCallback(WebsocketsMessage message) {
  Serial.print("Got Message: ");
  Serial.println(message.data());
  resp[0] = '\0';
  strcpy(resp, message.data().c_str());
  trimWhiteSpace(resp);
  processResponse(resp);
}

void onEventsCallback(WebsocketsEvent event, String data) {
  if (event == WebsocketsEvent::ConnectionOpened) {
    // client_connected = true;
    Serial.println("Connnection Opened");
  } else if (event == WebsocketsEvent::ConnectionClosed) {
    client_connected = false;
    Serial.println("Connnection Closed");
  } else if (event == WebsocketsEvent::GotPing) {
    Serial.println("Got a Ping!");
  } else if (event == WebsocketsEvent::GotPong) {
    Serial.println("Got a Pong!");
  }
}

WebsocketsClient client;

void setup() {
  Serial.begin(115200);
  pinMode(A1, OUTPUT);
  pinMode(A5, OUTPUT);
  pinMode(PIR, INPUT);
  pinMode(LED, OUTPUT);
  selectBrightness(2);

  {
    using namespace esp32cam;
    Config cfg;
    cfg.setPins(pins::AiThinker);
    cfg.setResolution(midRes);
    cfg.setBufferCount(2);
    cfg.setJpeg(80);
    bool ok = Camera.begin(cfg);
    //Serial.println(ok ? "CAMERA OK" : "CAMERA FAIL");
  }

  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(ssid, pswd);
  IPAddress IP = WiFi.softAPIP();

  client.onMessage(onMessageCallback);
  client.onEvent(onEventsCallback);

  //   Serial.println();
  //   Serial.println(IP);

  server.on("/", HTTP_GET, [](AsyncWebServerRequest* request) {
    request->send_P(200, "text/plain", "Hello!");
  });

  server.on("/set", HTTP_ANY, [](AsyncWebServerRequest* request) {
    if (request->method() == HTTP_GET) {
      request->send_P(200, "text/html", index_html);
    } else if (request->method() == HTTP_POST) {
      sta_ssid[0] = '\0';
      strcpy(sta_ssid, request->getParam(0)->value().c_str());
      sta_pswd[0] = '\0';
      strcpy(sta_pswd, request->getParam(1)->value().c_str());
      Serial.print("Set Params to: ");
      Serial.print(sta_ssid);
      Serial.print(" ");
      Serial.println(sta_pswd);
      WiFi.begin(sta_ssid, sta_pswd);
      request->send_P(200, "text/plain", "{success!}");
    }
  });

  server.on("/info", HTTP_GET, [](AsyncWebServerRequest* request) {
    if (WiFi.status() == WL_CONNECTED) {
      inp[0] = '\0';
      strcat(inp, "{");
      strcat(inp, "\"conn\":1,");
      strcat(inp, "\"rssi\":");
      char temp[16];
      itoa(WiFi.RSSI(), temp, 10);
      strcat(inp, temp);
      strcat(inp, ",\"ip\":");
      strcat(inp, WiFi.localIP().toString().c_str());
      strcat(inp, "}");
      Serial.println(inp);
      request->send_P(200, "text/plain", inp);
    } else {
      request->send_P(200, "text/plain", "{\"conn\":0}");
    }
  });

  server.begin();
  Serial.print("Connecting to: ");
  Serial.print(sta_ssid);
  Serial.print(" ");
  Serial.println(sta_pswd);
  WiFi.begin(sta_ssid, sta_pswd);
}

void stablink() {
  int w_stat = WiFi.status();
  if (w_stat == WL_CONNECTED) {
    if (millis() - t_stablink >= 500) {
      if (s_stablink) {
        digitalWrite(LED, LOW);
        s_stablink = !s_stablink;
      } else {
        digitalWrite(LED, HIGH);
        s_stablink = !s_stablink;
      }
      t_stablink = millis();
    }
  } else {
    if (millis() - t_stablink >= 100) {
      if (s_stablink) {
        digitalWrite(LED, LOW);
        s_stablink = !s_stablink;
      } else {
        digitalWrite(LED, HIGH);
        s_stablink = !s_stablink;
      }
      t_stablink = millis();
    }
    // reconnect();
  }
}

char* readStrList(char* memory, const char* strList, byte pos) {
  byte index = 0;
  memory[0] = '\0';
  for (int i = 0; i < strlen(strList); i++) {
    if (strList[i] == ',') {
      index++;
    }
    if (index == pos - 1) {
      strncat(memory, &strList[i], 1);
    }
  }
  if (memory[0] == ',') {
    strcpy(memory, memory + 1);
  }
  return memory;
}

bool isListData(const char* data) {
  if (data[0] == '[' && data[strlen(data) - 1] == ']') {
    return true;
  } else {
    return false;
  }
}

void trimWhiteSpace(char* str) {
  if (str == NULL) {
    return;
  }
  int len = strlen(str);
  int start = 0;
  int end = len - 1;
  while (isspace(str[start]) && start < len) {
    start++;
  }
  while (end >= start && isspace(str[end])) {
    end--;
  }
  int shift = 0;
  for (int i = start; i <= end; i++) {
    str[shift] = str[i];
    shift++;
  }
  str[shift] = '\0';
}

void substr(const char* input, char* output, int start, int stop) {
  if (start < 0 || start >= strlen(input) || stop < 0 || stop >= strlen(input) || start > stop) {
    output[0] = '\0';
  } else {
    strncpy(output, input + start, stop - start + 1);
    output[stop - start + 1] = '\0';
  }
}

void processResponse(char* res) {
  if (isListData(res)) {
    memo[0] = '\0';
    substr(res, memo, 1, strlen(res) - 2);
    res[0] = '\0';
    strcpy(res, memo);
    memo[0] = '\0';
    Serial.println(res);
    int person = atoi(readStrList(memo, res, 1));
    if (person > 0) {
      Serial.println("Person detected!");
      lastMillis = millis();
    }
    dark = atoi(readStrList(memo, res, 2)) > 0 ? true : false;
    Serial.println(dark ? "Dark" : "!Dark");
  }
}

void connectWS() {
  int w_stat = WiFi.status();
  if (w_stat == WL_CONNECTED && !client_connected && millis() - last_plug_millis >= 2000) {
    Serial.println("Connecting Socket...");
    client_connected = client.connect(ws_server);
    last_plug_millis = millis();
  }
}

void sendFrame() {
  if (client.available()) {
    if (millis() - last_frame_millis >= 200) {
      auto frame = esp32cam::capture();
      if (frame != nullptr) {
        client.sendBinary((const char*)frame->data(), frame->size());
        Serial.println("Frame Sent.");
      }
      last_frame_millis = millis();
    }
    client.poll();
  } else {
    // Serial.println("client unavailable.");
    // Serial.println(client_connected ? "client connected" : "client not connected");
  }
}

void selectBrightness(int val) {
  switch (val) {
    case 0:
      digitalWrite(A1, LOW);
      digitalWrite(A5, LOW);
      break;
    case 1:
      digitalWrite(A1, HIGH);
      digitalWrite(A5, LOW);
      break;
    case 2:
      digitalWrite(A1, LOW);
      digitalWrite(A5, HIGH);
      break;
    case 3:
      digitalWrite(A1, HIGH);
      digitalWrite(A5, HIGH);
      break;
  }
}

void handleBrightness() {
  diff = millis() - lastMillis;
  if (diff >= interval * 1000UL) {
    if (diff <= interval * 2000UL) {
      selectBrightness(1);
    } else {
      selectBrightness(0);
    }
  } else {
    selectBrightness(2);
  }
  if (dark && digitalRead(PIR)) {
    lastMillis = millis();
  }
}

void loop() {
  stablink();
  connectWS();
  sendFrame();
  handleBrightness();
}