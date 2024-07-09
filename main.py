import network
import aioespnow
import asyncio
# A WLAN interface must be active to send()/recv()
network.WLAN(network.STA_IF).active(True)
e = aioespnow.AIOESPNow()
e.active(True)
async def recv_till_halt(e):
    async for mac, msg in e:
        print(mac, msg)
        if msg == b'halt':
          break
asyncio.run(recv_till_halt(e))