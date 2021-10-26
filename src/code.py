# Proyecto Monitor CO2 
#   versión MagTag
#
# (C) 2021, Héctor Daniel Cortés González <hdcg@ier.unam.mx>
# (C) 2021, Laboratorio de Tecnologías Abiertas, LaTA+
# (C) 2021, Instituto de Energías Renovables
# (C) 2021, Universidad Nacional Autónoma de México
#
# CO2 Sensor: Sensirion SCD30
import time
tm=time.monotonic()
import board
import digitalio
led = digitalio.DigitalInOut(board.D13)
led.direction = digitalio.Direction.OUTPUT
led.value = True
import busio
import adafruit_scd30
import terminalio
import displayio
import alarm
import wifi
import adafruit_lis3dh
import adafruit_imageload
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_magtag.magtag import MagTag
from secrets import secrets

print("Start: ", tm)

SHORT_DELAY=0.128
DELAY=1.024
LONG_DELAY=8.192
MEASUREMENT_INTERVAL=2
POST_INTERVAL=180
CO2LOW=400
CO2MID=700
CO2HIGH=1000
PLAY_TONE=2
TONE_FRECUENCY=880
TONE_DURATION=0.333
SPLASH_IMAGE="/bmps/splash.bmp"
BIG_FONT="/fonts/DejaVuSans-Bold-75.pcf"
BAR_FONT="/fonts/DejaVuSans-18.pcf"

print("*" * 40)
print("MonitorCO2 MagTag version")
print("(C) 2021, hdcg@ier.unam.mx")
print("(C) 2021, LaTA+")
print("(C) 2021, IER-UNAM")
print("(C) 2021, UNAM")
print("*" * 40)
#
# Begin with SCD30, makes no sense no sensor working
#
# SCD-30 has tempremental I2C with clock stretching, datasheet recommends
# starting at 50KHz
i2c = busio.I2C(board.SCL, board.SDA, frequency=50000)
scd30 = adafruit_scd30.SCD30(i2c) 
if scd30.measurement_interval != MEASUREMENT_INTERVAL :
  scd30.measurement_interval = MEASUREMENT_INTERVAL
  print("Setting MSI=", scd30.measurement_interval)
if not scd30.self_calibration_enabled :
  scd30.self_calibration_enabled=True
  print("Setting ASC=", scd30.self_calibration_enabled)
#
# Accel also uses i2c
#
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x19)
lis3dh.range = adafruit_lis3dh.RANGE_2_G
if lis3dh.acceleration.y > 0 :
  rotate=270
else :
  rotate=90
lis3dh.data_rate = 0
#
# Splash image IER-UNAM on PowerOn
#
if not alarm.wake_alarm:
  print("powerOnSelfTest:")
  magtag=MagTag(default_bg=SPLASH_IMAGE)
  magtag.display.rotation=rotate
  magtag.add_text(
    text_font=BAR_FONT,
    text_position=(
      magtag.graphics.display.width - 2, 2
    ),
    text_anchor_point=(1.0, 0.0),
  )
  COLORS=[(255, 0, 0), (255,127,0), (255, 255, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255), (255, 0, 255), (255, 255, 255)]
  magtag.peripherals.neopixel_disable = False
  magtag.peripherals.neopixels.auto_write=False
  magtag.set_text(secrets["owner"])
  magtag.peripherals.play_tone(TONE_FRECUENCY, TONE_DURATION)
  while magtag.display.busy:
    for i in range(8):
      for j in range(3,0,-1):
        magtag.peripherals.neopixels[j]=magtag.peripherals.neopixels[j-1]
      magtag.peripherals.neopixels[0]=COLORS[i]
      magtag.peripherals.neopixels.show()
      time.sleep(SHORT_DELAY)
  for i in range(3):
    for j in range(3,0,-1):
      magtag.peripherals.neopixels[j]=magtag.peripherals.neopixels[j-1]
    magtag.peripherals.neopixels.show()
    time.sleep(SHORT_DELAY)
  magtag.peripherals.neopixel_disable = True
  led.value = False
  magtag.exit_and_deep_sleep(POST_INTERVAL)
#
# WokeUp!
#
magtag = MagTag()
display = magtag.display
display.rotation = rotate
#
# Make UI
#
# Make a background color fill
color_bitmap = displayio.Bitmap(display.width, display.height, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0xFFFFFF
backGround = displayio.TileGrid(color_bitmap, pixel_shader=color_palette)

bigFont=bitmap_font.load_font(BIG_FONT)

co2Bar = label.Label(
  bigFont,
  text="Error",
  color=0,
  anchor_point=(1.0, 0.5),
  anchored_position = (3 * display.width // 4 - 2, display.height // 2),
)

barFont = bitmap_font.load_font(BAR_FONT)

centerBar = label.Label(
  barFont, 
  text="CO2\nppm",
  color=0,
  anchor_point=(0.0, 0.5),
  anchored_position = (3 * display.width // 4 + 2, display.height // 2),
)

topBar = label.Label(
  barFont,
  text="1234567890" * 3,
  color=0,
  anchor_point=(0.0, 0.0),
  anchored_position = (2, 2),
)

bottomBar = label.Label(
  barFont,
  text="1234567890" * 3,
  color=0,
  anchor_point=(0.0, 1.0),
  anchored_position = (2, display.height - 2),
)

group = displayio.Group()
group.append(backGround)
group.append(co2Bar)
group.append(centerBar)
group.append(topBar)
group.append(bottomBar)

#
# First, get CO2 concentration 
#
while not scd30.data_available:
  time.sleep(0.5)
  
co2ppm=int(scd30.CO2)
co2Bar.text=str(co2ppm)

#
# Network operations
#
try:
  magtag.network.connect()
except Exception as e:
  topBar.text = str(e)

if magtag.network._wifi.is_connected :
  print("My IP address is", wifi.radio.ipv4_address)
  topBar.text = "[%s] (%ddBm)" % (wifi.radio.ap_info.ssid, wifi.radio.ap_info.rssi)
  
  try:
    response=magtag.get_local_time()
    print(response)
  except Exception as e:
    print(str(e))

lt=time.localtime()
  
vbat = magtag.peripherals.battery
print("vbat=", vbat)

bottomBar.text = "%02d:%02d %.1fV %+.1fC %.0f%%HR" % (lt.tm_hour, lt.tm_min, vbat, scd30.temperature, scd30.relative_humidity)
#
# transfer data
#
if magtag.network._wifi.is_connected:
  try:
    print("sending data...")
    magtag.network.push_to_io("magtag.co2ppm", co2ppm)
    magtag.network.push_to_io("magtag.temperature", scd30.temperature)
    magtag.network.push_to_io("magtag.relative-humidity", scd30.relative_humidity)
    magtag.network.push_to_io("magtag.vbat", vbat);
    magtag.network.push_to_io("magtag.rssi", wifi.radio.ap_info.rssi)
    print("data sent")
  except Exception as e:
    topBar.text = str(e)
#
# lights and sounds show
#
magtag.peripherals.neopixel_disable = False

light = magtag.peripherals.light
print("light=", light)

COLOR_INTENSITY=4+light//256
COLOR_GREEN=(0,COLOR_INTENSITY,0)
COLOR_YELLOW=(COLOR_INTENSITY,COLOR_INTENSITY,0)
COLOR_RED=(COLOR_INTENSITY,0,0)

display.show(group)
display.refresh()

if co2ppm>=CO2LOW and co2ppm<CO2MID:
  magtag.peripherals.neopixels.fill(COLOR_GREEN)
  if PLAY_TONE>2:
    magtag.peripherals.play_tone(TONE_FRECUENCY, TONE_DURATION)

if co2ppm>=CO2MID and co2ppm<CO2HIGH:
  magtag.peripherals.neopixels.fill(COLOR_YELLOW)
  if PLAY_TONE>1:
    magtag.peripherals.play_tone(TONE_FRECUENCY, TONE_DURATION)
    time.sleep(TONE_DURATION);
    magtag.peripherals.play_tone(TONE_FRECUENCY, TONE_DURATION)

if co2ppm>=CO2HIGH:
  magtag.peripherals.neopixels.fill(COLOR_RED)
  if PLAY_TONE>0:
    magtag.peripherals.play_tone(TONE_FRECUENCY, TONE_DURATION)
    time.sleep(TONE_DURATION);
    magtag.peripherals.play_tone(TONE_FRECUENCY, TONE_DURATION)
    time.sleep(TONE_DURATION);
    magtag.peripherals.play_tone(TONE_FRECUENCY, TONE_DURATION)

while magtag.display.busy: 
  time.sleep(SHORT_DELAY)

magtag.peripherals.neopixel_disable = True
#
# Clean up and exit (er, deep sleep)
#  
te=time.monotonic() - tm
print("TimeElapsed=", te)
if te>=POST_INTERVAL/2:
  ds = POST_INTERVAL
else:
  ds = POST_INTERVAL - te
print("DeepSleep=", ds)

led.value = False
magtag.exit_and_deep_sleep(ds)

