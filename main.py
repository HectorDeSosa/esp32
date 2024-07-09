
import network
import aioespnow
import asyncio
import uasyncio as asyncio
import time
import json
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
peer = b'0\xc9"2\xf6\xcc'   # MAC address of peer's wifi interface
e.add_peer(peer)
async def recv_till_halt(e):
    while True:
        async for mac, msg in e:
            print(mac, msg)
            if msg == b'halt':
                break
        await asyncio.sleep(5)
async def enviar(e,peer):
    while True:
        datos={'t':'topico','me':'prueba'}
        await e.asend(peer, json.dumps(datos).encode('utf-8'), True)
        print("enviado")
        await asyncio.sleep(20)
    
async def main(e,peer):
    task1 = asyncio.create_task(recv_till_halt(e))
    task2 = asyncio.create_task(enviar(e, peer))
    await asyncio.gather(task1, task2)
    
try:
    asyncio.run(main(e,peer))
finally:
    asyncio.new_event_loop()
