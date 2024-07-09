
import network
import aioespnow
import asyncio
import time

def wifi_reset():   # Reset wifi to AP_IF off, STA_IF on and disconnected
  sta = network.WLAN(network.STA_IF); sta.active(False)
  sta.active(True)
  while not sta.active():
      time.sleep(0.1)
  sta.disconnect()   # For ESP8266
  return sta

sta= wifi_reset()  # Reset wifi to AP off, STA on and disconnected
sta.connect('Tenda_702298', '5KKfrLg9')
sta.config(pm=sta.PM_NONE)
while not sta.isconnected():  # Wait until connected...
    time.sleep(0.1)

e = aioespnow.AIOESPNow()
e.active(True)
async def recv_till_halt(e):
    async for mac, msg in e:
        print(mac, msg)
        if msg == b'halt':
          break
asyncio.run(recv_till_halt(e))