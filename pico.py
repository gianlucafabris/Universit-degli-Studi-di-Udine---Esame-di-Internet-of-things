from machine import Pin, PWM, ADC
from umqtt.simple import MQTTClient
import network
from time import sleep

#LED e Joystick
led_r = PWM(Pin(6, Pin.OUT))
led_g = PWM(Pin(7, Pin.OUT))
led_b = PWM(Pin(8, Pin.OUT))
led_r.freq(1000)
led_g.freq(1000)
led_b.freq(1000)
joystick_x = ADC(Pin(26))
joystick_y = ADC(Pin(27))
joystick_button = Pin(22, Pin.IN, Pin.PULL_UP)

#MQTT
mqtt_client_id = "raspberry_pico"
mqtt_broker = "public.mqtthq.com"
mqtt_broker_port = 1883
mqtt_topic_joystick = "d1c51b726396f4649ccb187d42ec99c639ddc26269b97c95ea7f040a91c66da3_joystick"
mqtt_topic_led = "d1c51b726396f4649ccb187d42ec99c639ddc26269b97c95ea7f040a91c66da3_led"
mqtt_qos = 0
mqtt_retain = False

#LED e Joystick
def set_led(color):
    led_r.duty_u16(int(int(color[0:2], 16)/255*65535))
    led_g.duty_u16(int(int(color[2:4], 16)/255*65535))
    led_b.duty_u16(int(int(color[4:6], 16)/255*65535))

def get_joystick():
    x = round(joystick_x.read_u16()/65535*100, 1)
    y = round(joystick_y.read_u16()/65535*100, 1)
    b = 1 if not joystick_button.value() else 0
    return x, y, b

#MQTT
def on_message(topic, message):
    msg=str(message.decode("utf-8"))
    print("Mesasge recived ", msg, " " , topic)
    set_led(msg)

#wifi
def connect_to_wifi(ssid, password):
    wifi = network.WLAN(network.STA_IF)
    if not wifi.isconnected():
        print("Connessione al WIFI...")
        wifi.active(True)
        wifi.connect(ssid, password)
        while not wifi.isconnected():
            pass
    print("Connesso al WIFI")
    print(wifi.ifconfig())
    return wifi

#main
def main():
    global mqtt_client_id, mqtt_broker, mqtt_broker_port, mqtt_topic_joystick, mqtt_topic_led, mqtt_qos, mqtt_retain
    print("Press Ctrl+C to stop and exit!")

    #default state
    set_led("000000")
    try:
        #wifi
        wifi = connect_to_wifi("SSID", "PSW")

        #MQTT
        mqtt_client = MQTTClient(mqtt_client_id, mqtt_broker)
        mqtt_client.connect()
        print(f"Connected")
        mqtt_client.set_callback(on_message)
        mqtt_client.subscribe(mqtt_topic_led, mqtt_qos)
        print("\nSuccessfully subscribed!")

        #start
        while True:
            x, y, b = get_joystick()
            #pubblica messaggio joystick su MQTT
            data_joystick = f"{x},{y},{int(b)}"
            mqtt_client.publish(mqtt_topic_joystick, data_joystick, mqtt_retain, mqtt_qos)
            print("Message published", data_joystick)
            #leggi messaggi MQTT
            mqtt_client.check_msg()
            sleep(1)

    except KeyboardInterrupt:
        print("Uscita in corso...")
    finally:
        #stop
        mqtt_client.disconnect()
        wifi.active(False)

main()
