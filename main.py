
from mqtt_as import MQTTClient
from mqtt_local import config
import uasyncio as asyncio
#import uasyncio as asyncio
import dht, machine
import json
import ubinascii
from machine import unique_id
import uos as os
import btree
from collections import OrderedDict
#temperatura
#setpiont es flotante 
#periodo es flotante
#modo automatico/manual
#rele ON/OFF

CLIENT_ID = ubinascii.hexlify(unique_id()).decode('utf-8')

#fijar el orden del diccionario
parametros = OrderedDict([
    ('temperatura', 0.0),
    ('humedad', 0.0),
    ('periodo', 30),
    ('setpoint1', 23.5),
    ('modo1', 'manual'),
    ('setpoint2', 26.5),
    ('modo2', 'manual')
])
# sensor
d = dht.DHT22(machine.Pin(25))

# relé 1 ventilador 1
rele1 = machine.Pin(12, machine.Pin.OUT)
rele1.value(0)  # activo en bajo

# relé 2 ventilador 2
rele2 = machine.Pin(14, machine.Pin.OUT)
rele2.value(0)  # activo en bajo

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
                        rele1.value(1)
                        print("Rele encendido")
                    elif banrele == "OFF":
                        rele1.value(0)
                        print("Rele apagado")
        elif topicodeco== "rele2":
                banrele= msgdeco.upper()
                if parametros['modo2']=="manual":
                    if banrele == "ON":
                        rele2.value(1)
                        print("Rele encendido")
                    elif banrele == "OFF":
                        rele2.value(0)
                        print("Rele apagado")
        elif topicodeco == "periodo":
            parametros['periodo'] = float(msgdeco)
            cambio = True
    except Exception as e:
        print(f"Error: {e}")

    if cambio:
        escribir_db()

async def wifi_han(state):
    print('Wifi is ', 'up' if state else 'down')
    await asyncio.sleep(2)

async def conn_han(client):
    await client.subscribe('setpoint1', 1)
    await client.subscribe('modo1', 1)
    await client.subscribe('rele1', 1)
    await client.subscribe('setpoint2', 1)
    await client.subscribe('modo2', 1)
    await client.subscribe('rele2', 1)
    await client.subscribe('periodo', 1)

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
        
        await asyncio.sleep(parametros['periodo'])

async def main(client):
    await client.connect()
    await asyncio.sleep(4)  # Esperar para dar tiempo al broker
    while True:
        try:
            await client.publish(f"hector/{CLIENT_ID}", json.dumps(parametros, indent=4), qos=1)
        except OSError as e:
            print(f"Fallo al publicar: {e}")
        await asyncio.sleep(parametros['periodo'])  # Esperar según el periodo definido

async def task(client):
    await asyncio.gather(main(client), monitoreo())

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

config['subs_cb'] = sub_cb
config['connect_coro'] = conn_han
config['wifi_coro'] = wifi_han
config['ssl'] = True

if 'db' not in os.listdir():
    print("Creando base de datos...")
    escribir_db()
else:
    print("Leyendo base de datos...")
    leer_db()

MQTTClient.DEBUG = True  # Opcional
client = MQTTClient(config)
try:
    asyncio.run(task(client))
finally:
    client.close()
    asyncio.new_event_loop()
