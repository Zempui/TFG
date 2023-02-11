"""
Script que se encargará de generar un Dockerfile partiendo
de un archivo "config.yml".
Se emplear una "docker swarm" para el despliegue simultáneo
de los distintos nodos.
"""

from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from colorama import Fore



###############################
#  DEFINICIÓN DE EXCEPCIONES  #
###############################
class dockerfileException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
        

###############################
#   DEFINICIÓN DE FUNCIONES   #
###############################
def reader(lab:dict) -> tuple:
    """
    Función "reader" que tomará como parámetro un diccionario que contenga
    la definición del laboratorio de "config.yml" y devolverá una tupla con
    la red a la que hace referencia, la definición del broker y una tabla
    con la información de cada cliente.
    """
    network:str = lab["network"]
    broker:dict = {}
    nodes:list = []
    for i in lab["nodes"]:
        if i == "broker":
            broker = lab["nodes"][i]
            print(f"{Fore.GREEN}\tBroker añadido{Fore.RESET}")
        else:
            nodes.append(lab["nodes"][i])
            print(f"{Fore.GREEN}\tNodo [{i}] añadido{Fore.RESET}")
    return (network, broker, nodes)

def buscaParam(param:str, file, content:dict) -> bool:
    """
    Función "buscaParam", que buscará las ocurrencias de un parámetro
    en un archivo y las almacenará en un diccionario. Devuelve True si
    no ha habido ninguna ocurrencia.
    """
    notFound:bool = True
    for line in file:
        if param in line:
            notFound=False
            content[param]=line[line.find(param)+len(param)+1:].replace("\n","")
    file.seek(0,0)
    return notFound

def dockerfileGenerator(network:str, broker:dict, nodes:list) -> None:
    """
    Función "dockerfileGenerator", que tomará como parámetros la red a emplear,
    la configuración pertinente del broker y una lista de nodos. Generará el
    Dockerfile necesario para el despliegue del laboratorio virtual.
    En caso de error, lanzará una Excepción de tipo "dockerfileException"
    """
    try:
        dockerfile = open("Dockerfile", "w")
        brokerfile = open(f'{broker["build"]}/Dockerfile',"r")
        content:dict = {}
        # Buscamos los parámetros del Dockerfile del broker
        if (buscaParam("FROM", brokerfile, content)):
            raise(dockerfileException(f"Parámetro FROM no encontrado"))
        if (buscaParam("ADD",  brokerfile, content)):
            raise(dockerfileException(f"Parámetro ADD no encontrado"))
        # Corregimos el contenido de content["ADD"] para que tenga en cuenta
        # la carpeta contenedora del archivo.
        content["ADD"] = f'{broker["build"]}/{content["ADD"]}'
        print("content:",content)

    finally:
        dockerfile.close()
        brokerfile.close()

###############################
#      SCRIPT PRINCIPAL       #
###############################
def dockerize(debug:bool=False) -> None:
    file=open("./config.yml", "r")
    config:dict = load(file, Loader=Loader)
    try:
        (network, broker, nodes) = reader(config["lab"])
        print("Se ha leído config.yml correctamente")
        if debug: print(f"{Fore.BLUE}\tNetwork:\t{network}\n\tBroker:\t{broker}\n\tNodes:\t{nodes}{Fore.RESET}")
        dockerfileGenerator(network, broker, nodes)
    except KeyError as e:
        print(f'{Fore.RED}KeyError: No existe el parámetro {e} en config.yml{Fore.RESET}')
    except dockerfileException as e:
        print(f'{Fore.RED}Ha habido un problema en la generacinón del dockerfile: {e}{Fore.RESET}')
    except Exception as e:
        print(f"{Fore.RED}Ha ocurrido un error desconocido: {e}{Fore.RESET}")
    finally:
        file.close()


if __name__=="__main__":
    dockerize()