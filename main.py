import network
import aioespnow
import asyncio
import dht
from machine import Pin

# A WLAN interface must be active to send()/recv()
network.WLAN(network.STA_IF).active(True)

# Inicializar ESP-NOW
e = aioespnow.AIOESPNow()  # Returns AIOESPNow enhanced with async support
e.active(True)

# Dirección MAC del peer
peer =b'x\xe3m\x18N$'
e.add_peer(peer)

# Inicializar el sensor DHT22
sensor = dht.DHT22(Pin(25))  # Ajusta el pin según tu configuración

# Función para enviar datos periódicamente a un peer
async def heartbeat(e, peer, sensor, period=30):
    while True:
        sensor.measure()
        temp = sensor.temperature()
        hum = sensor.humidity()
        data = f'temp:{temp:.1f}C hum:{hum:.1f}%'.encode()
        
        if not await e.asend(peer, data):
            print("Heartbeat: peer not responding:", peer)
        else:
            print("Heartbeat:", data)
        
        await asyncio.sleep(period)

# Servidor de eco para devolver cualquier mensaje recibido al remitente
async def echo_server(e):
    async for mac, msg in e:
        print("Echo:", msg)
        try:
            await e.asend(mac, msg)
        except OSError as err:
            if len(err.args) > 1 and err.args[1] == 'ESP_ERR_ESPNOW_NOT_FOUND':
                e.add_peer(mac)
                await e.asend(mac, msg)

# Función principal para ejecutar las tareas asincrónicas
async def main(e, peer, sensor, timeout, period):
    asyncio.create_task(heartbeat(e, peer, sensor, period))
    asyncio.create_task(echo_server(e))
    await asyncio.sleep(timeout)

# Ejecutar la función principal
asyncio.run(main(e, peer, sensor, 600, 20))
