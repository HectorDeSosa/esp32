# (C) Copyright Peter Hinch 2017-2019.
# Released under the MIT licence.

# This demo publishes to topic "result" and also subscribes to that topic.
# This demonstrates bidirectional TLS communication.
# You can also run the following on a PC to verify:
# mosquitto_sub -h test.mosquitto.org -t result
# To get mosquitto_sub to use a secure connection use this, offered by @gmrza:
# mosquitto_sub -h <my local mosquitto server> -t result -u <username> -P <password> -p 8883

# Public brokers https://github.com/mqtt/mqtt.github.io/wiki/public_brokers

# red LED: ON == WiFi fail
# green LED heartbeat: demonstrates scheduler is running.

from mqtt_as import MQTTClient
from mqtt_local import config
import uasyncio as asyncio
#import uasyncio as asyncio
import dht, machine
import json
import ubinascii
import unique_id
import uos as os
from settings import BROKER
import btree
#temperatura
#humedad
#setpiont es flotante 
#periodo es flotante
#destello ON/OFF
#modo auto/manual
#rele ON/OFF

CLIENT_ID = ubinascii.hexlify(unique_id()).decode('utf-8')

parametros={
    'temperatura':0.0,
    'humedad':0.0,
    'setpoint':26.5,
    'periodo':10,
    'modo':'auto'
    }

#sensor
d = dht.DHT22(machine.Pin(25))

#led
led = machine.Pin(27, machine.Pin.OUT)
led.value(1)# activo en bajo
#el led inicialmente esta apagado

#rele
rele= machine.Pin(12, machine.Pin.OUT)
rele.value(1) #activo en bajo
#esta apagado

bandestello=False

#modificacion de parametros
def sub_cb(topic, msg, retained):
    #redibo y decodifico
    topicodeco=topic.decode()
    msgdeco=msg.decode()
    global bandestello
    cambio=False    
    #muestro el topico y el mensaje
    print('Topic = {} -> Valor = {}'.format(topicodeco, msgdeco))
    #condiciones para los topicos 
    if topicodeco == 'setpoint':
        try:
            parametros['setpoint']=float(msgdeco)
            cambio=True
        except OSError:
            print("ERROR, debe ser flotante")
    elif topicodeco == "periodo":
        try:
            parametros['periodo']=float(msgdeco)
            cambio=True
        except OSError:
            print("ERROR, debe ser flotante")
    elif topicodeco =="destello" :
        bandestello= (msgdeco.upper() == 'ON')#asigna True a bandestello si se cumple esto
        if bandestello == True:
            print("Destello activado")
        else:
            print("Destello desactivado")
    elif topicodeco=="modo":
        banmodo= msgdeco.lower()
        if banmodo == "manual":
            parametros['modo']=banmodo
            cambio=True
            print("Modo manual")
        elif banmodo == "auto":
            parametros['modo']=banmodo
            print("Modo automatico")
            cambio=True
        else:
            print("Modo incorrecto debe ser manual/auto")
    elif topicodeco== "rele":
        banrele= msgdeco.upper()
        if parametros['modo']=="manual":
            if banrele == "ON":
                rele.value(0)
                print("Rele encendido")
            elif banrele == "OFF":
                rele.value(1)
                print("Rele apagado")
    else:
        print("No hay dicho topico")
    
    if cambio is True:
        escribir_db()
async def wifi_han(state):
    print('Wifi is ', 'up' if state else 'down')
    await asyncio.sleep(1)

#subcripcion a los topicos 
async def conn_han(client):
    await client.subscribe('setpoint', 1)
    await client.subscribe('periodo', 1)
    await client.subscribe('modo', 1)
    await client.subscribe('destello', 1)
    await client.subscribe('rele', 1)

#lectura de temperatura y humedad
async def monitoreo():
    while True:
        d.measure()
        parametros['temperatura']=d.temperature()
        parametros['humedad']=d.humidity()
        if parametros['modo']=="auto":
            if parametros['temperatura']>parametros['setpoint']:
                parametros['rele']='ON'
                rele.value(0)#enciende rele
            else:
                parametros['rele']='OFF'
                rele.value(1)#apaga rele
        await asyncio.sleep(7)

#destellará por unos segundos 
#cuando reciba la orden "destello" por mqtt.
async def destello():
    global bandestello
    N=20
    while True:
        if bandestello==True:
            for i in range(N):
                led.value(0)
                await asyncio.sleep(0.5)
                led.value(1)
                await asyncio.sleep(0.5)
            bandestello=False
            
async def main(client):
    await client.connect()
    await asyncio.sleep(2)  # Esperar para dar tiempo al broker
    while True:
        try:
            await client.publish(f"iot/{CLIENT_ID}", json.dumps(parametros), qos=1)
        except OSError as e:
            print(f"Fallo al publicar: {e}")
        await asyncio.sleep(parametros['periodo'])  # Esperar según el periodo definido
  
async def task(client):
    # Ejecutar monitoreo(),destello() y main() en paralelo
    monitoreo_task = asyncio.create_task(monitoreo())
    destello_task = asyncio.create_task(destello())
    main_task=asyncio.create_task(main(client))
    await asyncio.gather(monitoreo_task, destello_task, main_task)

def escribir_db():
    with open("db", "w+b") as f:
        db = btree.open(f)
        db[b'setpoint'] = b"{}".format(str(parametros['setpoint']))
        db[b'periodo'] = b"{}".format(str(parametros['periodo']))
        db[b'modo'] = b"{}".format(str(parametros['modo']))
        db.flush()
        db.close()
    
def leer_db():
    with open("db", "r+b") as f:
        db = btree.open(f)
        parametros['setpoint']=db[b'setpoint']
        parametros['periodo']=db[b'periodo']
        parametros['modo']=db[b'modo']
        db.flush()
        db.close()

# Define configuration
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
# Set up client
MQTTClient.DEBUG = True  # Optional
client = MQTTClient(config)
try:
    asyncio.run(task(client))
finally:
    client.close()
    asyncio.new_event_loop()

