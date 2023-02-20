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



###############################
#  DEFINICIÓN DE EXCEPCIONES  #
###############################
class dockerComposeException(Exception):
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
    nodes:list = []
    for i in lab["nodes"]:
        nodes.append(lab["nodes"][i])
        print(f"{Fore.GREEN}\tNodo [{i}] añadido{Fore.RESET}")
    return (network, nodes)

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

def dockerComposeGenerator(network:str, nodes:list) -> None:
    """
    Función "dockerComposeGenerator", que tomará como parámetros la 
    red a emplear y una lista de nodos. Generará el
    docker-compose necesario para el despliegue del laboratorio virtual.
    En caso de error, lanzará una Excepción de tipo "dockerfileException"
    """
    try:
        compose = open("docker-compose.yml", "w")
        # TODO: Hay que diferenciar entre archivos con "build" e "image"
        content:dict = {}
        # Diferenciamos entre archivos con "build" e "image"
        for node in nodes:
            c1=False
            c2=False
            if not buscaParam("build", node, content[node]):
                #Caso 1: es un archivo con "build", su dockerfile estará en una carpeta
                c1=True
                try:
                    dockerfile = open(f"{content[node]['build']}/Dockerfile")
                    if (buscaParam("FROM", dockerfile, content[node])):
                        raise(dockerComposeException(f"{node}: Parámetro FROM no encontrado"))
                    if (buscaParam("ADD",  dockerfile, content[node])):
                        raise(dockerComposeException(f"{node}: Parámetro ADD no encontrado"))
                    # Corregimos el contenido de content["ADD"] para que tenga en cuenta
                    # la carpeta contenedora del archivo.
                    content["ADD"] = f'{content[node]["build"]}/{content["ADD"]}'
                finally:
                    dockerfile.close()

                
            if not buscaParam("image", node, content[node]):
                #Caso 2: es un archivo con "image"
                c2=True
                
            
            if(c1 and c2):
                del(content[node])
                raise(dockerComposeException(f"El nodo {node} contiene tanto 'build' como 'image'"))
            elif (not(c1 or c2)):
                raise(dockerComposeException(f"El nodo {node} no contiene ni 'build' ni 'image'"))


        
        
        print("content:",content)

    finally:
        compose.close()

###############################
#      SCRIPT PRINCIPAL       #
###############################
def dockerize(debug:bool=False) -> None:
    file=open("./config.yml", "r")
    config:dict = load(file, Loader=Loader)
    try:
        (network, nodes) = reader(config["lab"])
        print("Se ha leído config.yml correctamente")
        if debug: print(f"{Fore.BLUE}\tNetwork:\t{network}\n\tBroker:\t{broker}\n\tNodes:\t{nodes}{Fore.RESET}")
        dockerComposeGenerator(network, nodes)
    except KeyError as e:
        print(f'{Fore.RED}KeyError: No existe el parámetro {e} en config.yml{Fore.RESET}')
    except dockerComposeException as e:
        print(f'{Fore.RED}Ha habido un problema en la generacinón del docker-compose: {e}{Fore.RESET}')
    except Exception as e:
        print(f"{Fore.RED}Ha ocurrido un error desconocido: {e}{Fore.RESET}")
    finally:
        file.close()


if __name__=="__main__":
    dockerize()