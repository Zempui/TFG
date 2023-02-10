"""
Script que se encargará de generar un Dockerfile partiendo
de un archivo "config.yml".
"""

from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from colorama import Fore

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
    for i in lab["nodes"]:
        if i == "broker":
            broker = lab["nodes"][i]
            print(f"{Fore.GREEN}\tBroker añadido{Fore.RESET}")
        else:
            nodes.append(lab["nodes"][i])
            print(f"{Fore.GREEN}\tNodo [{i}] añadido{Fore.RESET}")
    return (network, broker, nodes)



try:
    (network, broker, nodes) = reader(config["lab"])
    print("Se ha leído config.yml correctamente")
    # print(f"""    Network: {network}
    # Broker: {broker}
    # Nodes: {nodes}""")
except KeyError as e:
    print(f'{Fore.RED}KeyError: No existe el parámetro {e} en config.yml{Fore.RESET}')
except Exception as e:
    print(f"{Fore.RED}Ha ocurrido un error desconocido: {e}{Fore.RESET}")