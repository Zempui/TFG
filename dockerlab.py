"""
Script que se encargará de generar un docker-compose partiendo
de un archivo "config.yml".
"""

from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from colorama import Fore
from typing import TypedDict, Optional


###############################
#  DEFINICIÓN DE TYPED DICTS  #
###############################
class Compose (TypedDict):
    version:str
    name:str
    services:dict
    networks:dict

class Service (TypedDict):
    build:Optional[str]
    image:Optional[str]
    entrypoint:Optional[str]
    depends_on:Optional[list]
    volumes:list
    networks:list

###############################
#  DEFINICIÓN DE EXCEPCIONES  #
###############################
class ReaderException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class ParseNodeException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
        

###############################
#   DEFINICIÓN DE FUNCIONES   #
###############################
def reader(config:dict, compose:Compose, *args, **conf) -> tuple:
    """
    Función "reader" que tomará como parámetro un diccionario que contenga
    la definición del laboratorio de "config.yml" y el diccionario mediante 
    el cual se generará el docker-compose. Comprobará que sólo hay
    una clave definida en dicho diccionario y dividirá su contenido en dos
    diccionarios, "network" y "nodes". Guardará el nombre de la clave en el
    diccionario "compose".
    """
    network:str = "10.0.0.0/8"
    nodes:dict = {}

    #Comprobamos que sólo hay una clave en "config"
    if(len(config) != 1):
        raise(ReaderException(f"'config' contiene {len(config)} elementos. Sólo se admite 1."))
    else:
        if conf["debug"]: print(f"{Fore.BLUE}Contenido del laboratorio: {config[list(config)[0]]}{Fore.RESET}")
        # Comprobamos el contenido de "config", de momento, sólo se admiten las cláusulas
        # "network" y "nodes"
        lab = config[list(config)[0]]
        if len(lab) > 2:
            raise(ReaderException(f"Se han definido más parámetros de los admitidos: {list(lab)}"))
        else:
            compose["name"]=list(config)[0]
            try:
                network = lab["network"]
                print(f"{Fore.GREEN}\tRed [{network}] añadida{Fore.RESET}")
            except KeyError:
                if "debug" in conf and conf["debug"]: 
                    print(f"{Fore.BLUE}'network' no está definido. Proporcionando el valor por defecto.")
            try:
                nodes = lab["nodes"]
                for node in nodes:
                    print(f"{Fore.GREEN}\tNodo [{node}] añadido{Fore.RESET}")
            except KeyError:
                if "debug" in conf and conf["debug"]: 
                    print(f"{Fore.BLUE}'nodes' no está definido. Proporcionando el valor por defecto.")
    return(network, nodes)


def generateNetwork(network:str, compose:Compose, *args, **conf) -> None:
    """
    Función "generateNetwork", que plasma los contenidos de "network"
    en el diccionario "compose".
    """
    compose["networks"]={f"{compose['name']}_network":
                                {"driver":"bridge",
                                "ipam":{"driver":"default",
                                        "config":[{"subnet":network}]}}}
    if "debug" in conf and conf["debug"]:
        print(f"{Fore.BLUE}\tnetworks: {compose['networks']}{Fore.RESET}")



def parseNode(nodes:dict, compose:Compose, *args, **conf) -> None:
    """
    Función "parseNode" que, para cada nodo, 
    parseará su contenido en el diccionario "compose"
    """
    compose["services"]={}
    for node in nodes:
        case1, case2 = False, False
        if "build" in nodes[node]: case1=True
        if "image" in nodes[node]: case2=True

        if(case1 and case2):
            raise ParseNodeException(f"El nodo {node} contiene cláusulas 'build':{nodes[node]['build']} e 'image':{nodes[node]['image']}")
        elif not(case1 or case2):
            raise ParseNodeException("El nodo no contiene cláusulas 'build' ni 'image'")
        else:
            service:Service = {}
            if case1:   #Caso 1: contiene "build"
                service["build"] = nodes[node]["build"]
            elif case2: #Caso 2: contiene "image"
                service["image"] = nodes[node]["image"]

            if "needs" in nodes[node]:  service["depends_on"] = nodes[node]["needs"]
            if "script" in nodes[node]: service["entrypoint"] = nodes[node]["script"]
            service ["volumes"]  = ["./:/workspace"]
            service ["networks"] = [list(compose["networks"])[0]]
            if "debug" in conf and conf["debug"]: 
                print(f"{Fore.BLUE}\tservice '{node}':\n\t\t{service}{Fore.RESET}")
            compose["services"][node]=service

                



###############################
#      SCRIPT PRINCIPAL       #
###############################
def dockerlab(debug:bool=False) -> None:
    file = open("./config.yml", "r")
    compose_file = open("./docker-compose.yml", "w")
    config:dict = load (file, Loader=Loader)
    compose:Compose = {}
    compose["version"]="1.0.0"
    try:
        (network, nodes) = reader(config, compose, debug=debug)
        print("Se ha leído config.yml correctamente")
        if debug: print(f"{Fore.BLUE}\tNetwork:\t{network}\n\tNodes:\t{nodes}{Fore.RESET}")
        generateNetwork(network, compose, debug=debug)
        print("Red implementada correctamente.")
        parseNode(nodes, compose, debug=debug)

        dump(compose, compose_file)


    except KeyError as e:
        print(f'{Fore.RED}KeyError: No existe el parámetro {e} en config.yml{Fore.RESET}')
    except ReaderException as e:
        print(f"{Fore.RED}Ha habido un problema en la lectura: \n\t{e}{Fore.RESET}")
    except ParseNodeException as e:
        print(f'{Fore.RED}Ha habido un problema en el parseo de elementos: \n\t{e}{Fore.RESET}')
    except Exception as e:
        print(f"{Fore.RED}Ha ocurrido un error desconocido: \n\t{e}{Fore.RESET}")
    finally:
        file.close()
        compose_file.close()


if __name__=="__main__":
    dockerlab(debug=True)