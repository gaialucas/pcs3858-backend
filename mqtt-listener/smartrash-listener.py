#  Copyright (c) 2022 Lucas Gaia <lucas.gaia.castro@usp.br>
"""Paho MQTT Listener for Smartrash.

The listener runs in a docker compose with the MQTT broker hosted at 'mosquitto'
and listens to the topic 'pcs3858/smartrash'. Each message has the form of:
id=X hi=Y ... wi=Z ...
Where id is the trashcan identification number, hi and wi are the i-th height
or wieght measure from the trashcan. An id may have multiple height or weight
measures but always only one id. The message is sent as a raw string, with fields
separated by whitespaces.
"""
import paho.mqtt.client as mqtt_client
import psycopg2
from configparser import ConfigParser

import random
from datetime import datetime
import sys

# broker = '0.0.0.0'
broker = 'mosquitto'
port = 1883
topic = "pcs3858/smartrash/#"
# generate client ID with pub prefix
client_id = f'python-mqtt-99'
# username = 'emqx'
# password = 'public'
db_conn = None
weight = 0.0
height = 0.0
id_meas = 7
id_trash = 1

def connect_mqtt() -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id)
    # client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        t_received = datetime.now()
        print(f"{t_received}: Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        msg_dict = {}
        for field_value_tuple in msg.payload.decode().split():
            k,v = field_value_tuple.split('=')
            msg_dict.update({k: v})
        print(msg_dict.items())
        sys.stdout.flush()
        client.publish('pcs3858/acks', 'OK')

        # save to DB ->
        cur = db_conn.cursor()
        weight += random.random()
        height += random.random()
        cur.execute(f"INSERT INTO smartrash.measures VALUES ({id_meas}, {weight}, {height}, {datetime.now().seconds()}, {id_trash});")
        id_meas += 1

    client.subscribe(topic)
    client.on_message = on_message


def read_postgres_cfg(filename='database.ini', section='postgresql'):
    """Read PostgreSQL parameters from ini file."""
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)

    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception(f'Section {section} not found in the {filename} file')

    return db


def connect_postgres(): # -> psycopg2.
    """Connect to PostgreSQL instance."""
    dbcfg = read_postgres_cfg()
    print(f"DB URL: {dbcfg['host']}")
    sys.stdout.flush()
    return psycopg2.connect(**dbcfg)


def run():
    db_conn = connect_postgres()
    client = connect_mqtt()
    subscribe(client)
    client.loop_forever()


if __name__ == '__main__':
    run()