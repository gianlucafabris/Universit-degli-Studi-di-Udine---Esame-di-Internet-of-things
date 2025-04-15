import paho.mqtt.client as mqtt
from time import sleep
import signal
import sys
import colorsys

from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_SENSOR, CATEGORY_LIGHTBULB
import pyhap.loader as loader

#HAP
hap_driver = AccessoryDriver(port=51826)
hap_joystick_x = None
hap_joystick_y = None
hap_joystick_b = None
hap_led = None

#MQTT
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client_id = "bridge_HAP"
mqtt_broker = "public.mqtthq.com"
mqtt_broker_port = 1883
mqtt_topic_joystick = "d1c51b726396f4649ccb187d42ec99c639ddc26269b97c95ea7f040a91c66da3_joystick"
mqtt_topic_led = "d1c51b726396f4649ccb187d42ec99c639ddc26269b97c95ea7f040a91c66da3_led"
mqtt_qos = 0
mqtt_retain = False

#HAP
class Joystick(Accessory):
    category = CATEGORY_SENSOR

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        serv_temperature = self.add_preload_service("TemperatureSensor", ["CurrentTemperature"])
        self.char_temperature = serv_temperature.configure_char("CurrentTemperature")

        #default state
        self.char_temperature.set_value(0)

    def set_temperature(self, value):
        self.char_temperature.set_value(value)

class LED(Accessory):
    category = CATEGORY_LIGHTBULB

    def __init__(self, *args, **kwargs):
        global mqtt_client, mqtt_topic_led, mqtt_qos, mqtt_retain
        super().__init__(*args, **kwargs)

        serv_light = self.add_preload_service("Lightbulb", ["On", "Hue", "Saturation", "Brightness"])

        self.char_on = serv_light.configure_char("On", setter_callback=self.set_on)
        self.char_hue = serv_light.configure_char("Hue", setter_callback=self.set_hue)
        self.char_saturation = serv_light.configure_char("Saturation", setter_callback=self.set_saturation)
        self.char_brightness = serv_light.configure_char("Brightness", setter_callback=self.set_brightness)

        self.mqtt_client = mqtt_client
        self.mqtt_topic_led = mqtt_topic_led
        self.mqtt_qos = mqtt_qos
        self.mqtt_retain = mqtt_retain

        #default state
        self.on = 0
        self.hue = 0
        self.saturation = 0
        self.brightness = 0
        msg_info = self.mqtt_client.publish(self.mqtt_topic_led, "000000", self.mqtt_qos, self.mqtt_retain)
        msg_info.wait_for_publish()

    def set_on(self, value):
        self.on = value
        self.send_message()

    def set_hue(self, value):
        self.hue = value
        self.send_message()

    def set_saturation(self, value):
        self.saturation = value
        self.send_message()

    def set_brightness(self, value):
        self.brightness = value
        self.send_message()

    def send_message(self):
        if self.on == 0:
            led_data = "000000"
        else:
            h = self.hue/360.0
            s = self.saturation/100.0
            b = self.brightness/100.0
            r, g, b = colorsys.hsv_to_rgb(h, s, b)
            r = format(int(r*255), "02x")
            g = format(int(g*255), "02x")
            b = format(int(b*255), "02x")
            led_data = f"{r}{g}{b}"
        msg_info = self.mqtt_client.publish(self.mqtt_topic_led, led_data, self.mqtt_qos, self.mqtt_retain)
        msg_info.wait_for_publish()

#MQTT
def on_subscribe(mqtt_client, userdata, mid, reason_code_list, properties):
    if reason_code_list[0].is_failure:
        print(f"\nBroker rejected you subscription: {reason_code_list[0]}")
    else:
        print(f"\nBroker granted the following QoS: {reason_code_list[0].value}")

def on_unsubscribe(mqtt_client, userdata, mid, reason_code_list, properties):
    if len(reason_code_list) == 0 or not reason_code_list[0].is_failure:
        print("\nSuccessfully unsubscribed!")
    else:
        print(f"\nBroker error: {reason_code_list[0]}")
    mqtt_client.disconnect()

def on_message(mqtt_client, userdata, message):
    global hap_joystick_x, hap_joystick_y, hap_joystick_b
    msg=str(message.payload.decode("utf-8"))
    # userdata.append(msg)
    print("Mesasge recived ", msg, " " , message.topic)
    x, y, b = msg.split(",")
    hap_joystick_x.set_temperature(float(x))
    hap_joystick_y.set_temperature(float(y))
    hap_joystick_b.set_temperature(int(b))

def on_publish(mqtt_client, userdata, mid, reason_code, properties):
    print("Message published (%d)" %mid)

def on_connect(mqtt_client, userdata, flags, reason_code, properties):
    global mqtt_topic_joystick, mqtt_qos
    if reason_code.is_failure:
        print(f"\nFailed to connect: {reason_code}. loop_forever() will retry connection")
    else:
        print(f"Connected")
        mqtt_client.subscribe(mqtt_topic_joystick, mqtt_qos)

#main
def signal_handler(sig, frame):
    global hap_driver, mqtt_client, mqtt_topic_joystick
    print("Uscita in corso...")
    hap_driver.signal_handler()
    mqtt_client.unsubscribe(mqtt_topic_joystick)
    mqtt_client.disconnect()
    mqtt_client.loop_stop()
    sys.exit(0)

def main():
    global hap_driver, hap_joystick_x, hap_joystick_y, hap_joystick_b, hap_led, mqtt_client
    #stop
    print("Press Ctrl+C to stop and exit!")
    signal.signal(signal.SIGTERM, signal_handler)

    #MQTT
    mqtt_client.on_subscribe = on_subscribe
    mqtt_client.on_unsubscribe = on_unsubscribe
    mqtt_client.on_message = on_message
    mqtt_client.on_publish = on_publish
    mqtt_client.on_connect = on_connect

    mqtt_client.user_data_set([])
    mqtt_client.connect(mqtt_broker, mqtt_broker_port)

    #HAP
    hap_joystick_x = Joystick(hap_driver, "Joystick X")
    hap_joystick_y = Joystick(hap_driver, "Joystick Y")
    hap_joystick_b = Joystick(hap_driver, "Joystick B")
    hap_led = LED(hap_driver, "LED RGB")
    bridge = Bridge(hap_driver, "Bridge HAP MQTT")
    bridge.add_accessory(hap_joystick_x)
    bridge.add_accessory(hap_joystick_y)
    bridge.add_accessory(hap_joystick_b)
    bridge.add_accessory(hap_led)
    hap_driver.add_accessory(bridge)

    #start
    mqtt_client.loop_start()
    hap_driver.start()

main()
