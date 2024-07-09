
from mqtt_as import MQTTClient
from mqtt_local import config
import uasyncio as asyncio
import json
import ubinascii
from machine import unique_id
import uos as os
import btree
from collections import OrderedDict
import network
import aioespnow
from settings import PEER_CLIENTE
#temperatura
#setpiont es flotante 
#periodo es flotante
#modo automatico/manual
#rele ON/OFF

CLIENT_ID = ubinascii.hexlify(unique_id()).decode('utf-8')

#fijar el orden del diccionario 195 Bytes
parametros = OrderedDict([
    ('temperatura', 0.0),
    ('humedad', 0.0),
    ('periodo', 30),
    ('setpoint1', 23.5),
    ('modo1', 'manual'),
    ('rele1', 'OFF'),
    ('setpoint2', 26.5),
    ('modo2', 'manual'),
    ('rele2', 'OFF')
])
def sub_cb(topic, msg, retained):
    topicodeco = topic.decode()
    msgdeco = msg.decode()
    global parametros
    cambio = False
    print('Topic = {} -> Valor = {}'.format(topicodeco, msgdeco))
    try:
        if topicodeco == 'setpoint1':
            parametros['setpoint1'] = float(msgdeco)
            cambio = True
        elif topicodeco == 'setpoint2':
            parametros['setpoint2'] = float(msgdeco)
            cambio = True
        elif topicodeco == "modo1":
            banmodo = msgdeco.lower()
            if banmodo in ["manual", "automatico"]:
                parametros['modo1'] = banmodo
                cambio = True
                print(f"Modo {banmodo}")
        elif topicodeco == "modo2":
            banmodo = msgdeco.lower()
            if banmodo in ["manual", "automatico"]:
                parametros['modo2'] = banmodo
                cambio = True
                print(f"Modo {banmodo}")
        elif topicodeco== "rele1":
                banrele= msgdeco.upper()
                if parametros['modo1']=="manual":
                    if banrele == "ON":
                        parametros['rele1']=banrele
                        cambio=True
                        print("Rele encendido")
                    elif banrele == "OFF":
                        parametros['rele1']=banrele
                        cambio=True
                        print("Rele apagado")
        elif topicodeco== "rele2":
                banrele= msgdeco.upper()
                if parametros['modo2']=="manual":
                    if banrele == "ON":
                        parametros['rele2']=banrele
                        cambio=True
                        print("Rele encendido")
                    elif banrele == "OFF":
                        parametros['rele2']=banrele
                        cambio=True
                        print("Rele apagado")
        elif topicodeco == "periodo":
            parametros['periodo'] = float(msgdeco)
            cambio = True
    except Exception as e:
        print(f"Error: {e}")
    if cambio:
        asyncio.create_task(enviar(topicodeco,msgdeco))

async def wifi_han(state):
    print('Wifi is ', 'up' if state else 'down')
    await asyncio.sleep(2)
#como cada 30s manda los datos de temperatura y huemedad
#tambien los leeo en el mismo tiempo.
async def recibir(e):
    while True:
        try:
            #se maneja asincronicamente esperando a que haya datospara ser leidos
            #reanuda el bucle solo cuando hay nuevos datos disponibles
            async for mac, msg in e:
                # Decodifica el bytearray a una cadena
                # Convierte la cadena JSON a un diccionario
                datos = json.loads(msg.decode('utf-8'))
                parametros['temperatura']=datos['t']
                parametros['humedad']=datos['h']
                print("recibiendo")
        except Exception as ex:
            print(f"Error: {ex}")
        await asyncio.sleep(1)

async def enviar (topicodeco, msgdeco):
    global e 
    peer=b'0\xc9"2\xf6\xcc'
    enviados={'to':topicodeco, 'm':msgdeco}
    await e.asend(peer,json.dumps(enviados).encode('utf-8'), True)

    
async def publicar(client):
    await client.connect()
    await asyncio.sleep(4) # Esperar para dar tiempo al broker
    while True:
        try:
            await client.publish(f"hector/{CLIENT_ID}", json.dumps(parametros), qos=1)
            datos={'temperatura':parametros['temperatura'] , 'humedad':parametros['humedad'] }
            await client.publish(f"sensores_remotos/{CLIENT_ID}", json.dumps(datos),qos=1)
        except OSError as e:
            print(f"Fallo al publicar: {e}")
        await asyncio.sleep(parametros['periodo'])  # Esperar según el periodo definido

async def main(client, e, peer):
    task1 = asyncio.create_task(publicar(client))
    task2 = asyncio.create_task(recibir(e))
    await asyncio.gather(task1, task2)

async def conn_han(client):
    await client.subscribe('setpoint1', 1)
    await client.subscribe('modo1', 1)
    await client.subscribe('rele1', 1)
    await client.subscribe('setpoint2', 1)
    await client.subscribe('modo2', 1)
    await client.subscribe('rele2', 1)
    await client.subscribe('periodo', 1)
    
config['subs_cb'] = sub_cb
config['connect_coro'] = conn_han
config['wifi_coro'] = wifi_han
config['ssl'] = True

MQTTClient.DEBUG = True  # Opcional
client = MQTTClient(config)
# A WLAN interface must be active to send()/recv()
sta = network.WLAN(network.STA_IF)  # Or network.AP_IF
sta.active(True)
sta.disconnect()
e = aioespnow.AIOESPNow()
e.active(True)
peer = b'0\xc9"2\xf6\xcc'   # MAC address of peer's wifi interface
e.add_peer(peer)
try:
    asyncio.run(main(client, e, peer))
finally:
    client.close()
    asyncio.new_event_loop()
