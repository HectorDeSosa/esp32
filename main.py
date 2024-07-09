#clienteee
import uasyncio as asyncio
import dht, machine
import json
import ubinascii
from machine import unique_id
import uos as os
import btree
from collections import OrderedDict
import network
import aioespnow
from settings import PEER_SERVER
#temperatura y humedad
#setpiont es flotante 
#periodo es flotante
#modo automatico/manual
#rele ON/OFF
"""
#saber mac
import network
wlan_sta = network.WLAN(network.STA_IF)
wlan_sta.active(True)
wlan_mac = wlan_sta.config('mac')
print("MAC Address:", wlan_mac)
print("MAC Address:", wlan_mac.hex())
"""
CLIENT_ID = ubinascii.hexlify(unique_id()).decode('utf-8')

#print("MAC Address:", wlan_mac.hex())
#fijar el orden del diccionario
parametros = OrderedDict([
    ('temperatura', 0.0),
    ('humedad', 0.0),
    ('periodo',60.0),
    ('setpoint1', 23.5),
    ('modo1', 'manual'),
    ('rele1', 'OFF'),
    ('setpoint2', 26.5),
    ('modo2', 'manual'),
    ('rele2', 'OFF')
])
# sensor
d = dht.DHT22(machine.Pin(25))

# relé 1 ventilador 1
rele1 = machine.Pin(12, machine.Pin.OUT)
rele1.value(0)  # activo en alto

# relé 2 ventilador 2
rele2 = machine.Pin(14, machine.Pin.OUT)
rele2.value(0)  # activo en alto

async def topicos(msg):
    recibido = json.loads(msg.decode('utf-8'))
    topicodeco = recibido['to']
    msgdeco = recibido['m']
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
                        rele1.value(1)
                        print("Rele encendido")
                    elif banrele == "OFF":
                        parametros['rele1']=banrele
                        cambio=True
                        rele1.value(0)
                        print("Rele apagado")
        elif topicodeco== "rele2":
                banrele= msgdeco.upper()
                if parametros['modo2']=="manual":
                    if banrele == "ON":
                        parametros['rele2']=banrele
                        cambio=True
                        rele2.value(1)
                        print("Rele encendido")
                    elif banrele == "OFF":
                        parametros['rele2']=banrele
                        cambio=True
                        rele2.value(0)
                        print("Rele apagado")
        elif topicodeco == "periodo":
            parametros['periodo'] = float(msgdeco)
            cambio = True
    except Exception as e:
        print(f"Error: {e}")
    if cambio:
        escribir_db()

async def recibir(e):
    while True:
        try:
            async for mac, msg in e:
                await topicos(msg)
                print("recibido")
        except Exception as ex:
            print(f"Error: {ex}")
        await asyncio.sleep(1)
async def enviar(e, peer):
    while True:
        try:
            enviado = {'t': parametros['temperatura'], 'h': parametros['humedad']}
            await e.asend(peer, json.dumps(enviado).encode('utf-8'), True)
            print("Datos enviados correctamente")
        except Exception as e:
            print(f"Error en el envío de datos: {e}")
        
        await asyncio.sleep(parametros['periodo'])

async def monitoreo():
    while True:
        try:
            d.measure()
            parametros['temperatura'] = d.temperature()
            parametros['humedad'] = d.humidity()
            if parametros['modo1'] == "automatico":
                if parametros['temperatura'] > parametros['setpoint1']:
                    parametros['rele1'] = 'ON'
                    rele1.value(1)  # enciende rele
                else:
                    parametros['rele1'] = 'OFF'
                    rele1.value(0)  # apaga rele
            if parametros['modo2'] == "automatico":
                if parametros['temperatura'] > parametros['setpoint2']:
                    parametros['rele2'] = 'ON'
                    rele2.value(1)  # enciende rele
                else:
                    parametros['rele2'] = 'OFF'
                    rele2.value(0)  # apaga rele
        except Exception as e:
            print(f"Error en monitoreo: {e}")
        
        await asyncio.sleep(20)

async def main(e, peer):
    task1 = asyncio.create_task(monitoreo())
    task2 = asyncio.create_task(enviar(e, peer))
    task3 = asyncio.create_task(recibir(e))
    await asyncio.gather(task1, task2, task3)
def escribir_db():
    with open("db", "w+b") as f:
        db = btree.open(f)
        db[b'periodo'] = b"{}".format(str(parametros['periodo']))
        db[b'setpoint1'] = b"{}".format(str(parametros['setpoint1']))
        db[b'modo1'] = b"{}".format(str(parametros['modo1']))
        db[b'setpoint2'] = b"{}".format(str(parametros['setpoint2']))
        db[b'modo2'] = b"{}".format(str(parametros['modo2']))
        db.flush()
        db.close()

def leer_db():
    with open("db", "r+b") as f:
        db = btree.open(f)
        parametros['periodo'] = float(db[b'periodo'].decode())
        parametros['setpoint1'] = float(db[b'setpoint1'].decode())
        parametros['modo1'] = db[b'modo1'].decode()
        parametros['setpoint2'] = float(db[b'setpoint2'].decode())
        parametros['modo2'] = db[b'modo2'].decode()
        db.flush()
        db.close()

if 'db' not in os.listdir():
    print("Creando base de datos...")
    escribir_db()
else:
    print("Leyendo base de datos...")
    leer_db()
    
# A WLAN interface must be active to send()/recv()
sta = network.WLAN(network.STA_IF)  # Or network.AP_IF
sta.active(True)
e = aioespnow.AIOESPNow() 
e.active(True)
peer = b'x\xe3m\x18N$'   # MAC address of peer's wifi interface
e.add_peer(peer)
try:
    asyncio.run(main(e,peer))
finally:
    asyncio.new_event_loop()