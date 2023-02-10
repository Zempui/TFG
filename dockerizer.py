"""
Script que se encargará de generar un Dockerfile partiendo
de un archivo "config.yml".
"""

from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

config:dict = load(open("./config.yml", "r"), Loader=Loader)

def reader(lab:dict):
    """
    Función reader que tomará como parámetro un diccionario que contenga
    la definición del laboratorio de "config.yml" y devolverá una tupla con
    la red a la que hace referencia, la definición del broker y una tabla
    con la información de cada cliente.
    """
    network:str = lab["network"]
    broker:dict = {}
    nodes = []
    j:int = 0
    for i in lab["nodes"]:
        if i == "broker":
            broker = lab[i]
        else:
            nodes[j]=lab["nodes"][i]
            j+=1
    return (network, broker, nodes)



try:
    network, broker, nodes = reader(config["lab"])
    print("Se ha leído config.yml correctamente")
except KeyError:
    print('KeyError: No existe el parámetro "lab" en config.yml')
except Exception:
    print("Ha ocurrido un error desconocido")