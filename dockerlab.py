"""
El presente repositorio muestra una herramienta para automatizar el despliegue de laboratorios virtuales mediante Docker. 
Se trata de un Trabajo de Fin de Grado (TFG) desarrollado en el curso 2022/23 para el Grado en Ingeniería de las Tecnologías de 
Telecomunicación de la Universidad de Sevilla.
"""

from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from colorama import Fore, Back
from typing import TypedDict, Optional
from ipaddress import ip_address, ip_network, IPv4Address, IPv4Network
import copy
import argparse
import subprocess
import shlex
from pynput import keyboard
from threading import Thread
import signal
import os
import docker
import re
import PySimpleGUI as sg
import time


###############################
#  DEFINICIÓN DE TYPED DICTS  #
###############################
class Arguments(TypedDict):
    build:bool
    execute:bool
    monitor:bool
    usage:bool

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
    deploy:Optional[dict]
    volumes:list
    networks:list
    cap_add:Optional[list] #Sólo para nodo de monitorización

###############################
#  DEFINICIÓN DE EXCEPCIONES  #
###############################
class ReaderException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class ParseNodeException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class IpAddrException(Exception):
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

    El nombre "sniffer" está reservado para el nodo de monitorización y si
    se añade un nodo con este nombre, será eliminado a la hora de ejecutar
    el programa y monitorizar los recursos
    """
    network:IPv4Network = ip_network("10.0.0.0/8")
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
                network = ip_network(lab["network"])
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


def generate_network(network:IPv4Network, compose:Compose, *args, **conf) -> None:
    """
    Función "generate_network", que plasma los contenidos de "network"
    en el diccionario "compose".
    """
    name = f"{compose['name']}_network"
    compose["networks"]={f"{name}":
                                {"name":f"{name}",
                                "external":True}}
    client = docker.from_env()
    try:
        client.networks.create(name=name, driver="bridge", ipam={"Config":[{"subnet":f"{network}"}]}, check_duplicate=True)
    except docker.errors.APIError:
        # Red creada anteriormente o red con la misma IP
        for i in client.networks.list():
            if ((i.name not in {"none", "host", "bridge"} and
                    len(i.attrs["IPAM"]["Config"])>0 and                    
                    "Subnet" in i.attrs["IPAM"]["Config"][0] and            
                    (ip_network(i.attrs["IPAM"]["Config"][0]["Subnet"]).subnet_of(network) or
                     ip_network(i.attrs["IPAM"]["Config"][0]["Subnet"]).supernet_of(network))) or 
                     i.name==name):
                client.networks.get(i.attrs["Id"]).remove()

        client.networks.create(name=name, driver="bridge", ipam={"Config":[{"subnet":f"{network}"}]}, check_duplicate=True)

    if "debug" in conf and conf["debug"]:
        print(f"{Fore.BLUE}\tnetworks: {compose['networks']}{Fore.RESET}")


def new_ip_addr(network:IPv4Network, ip_list:set[IPv4Address], n:int) -> list[IPv4Address]:
    """
    Función "new_ip_addr". Toma como parámetros una red IPv4, una lista de direcciones IP y un
    número de direcciones a obtener. Lanza una excepción en caso de que no hayan suficientes
    direcciones disponibles en la subred.
    """
    
    result:list[IPv4Address] = []
    if n>=1:
        for addr in network:
            if (not (addr in ip_list)               # Si la IP no está en la lista
                    and addr.packed[3:]!=b'\x00'    # Si la IP no acaba en '.0'
                    and addr.packed[3:]!=b'\x01'    # Si la IP no acaba en '.1' (Host)
                    and addr.packed[3:]!=b'\xff'):  # Si la IP no acaba en '.255'
                result.append(addr)
                n -= 1
            if n<1: break
        if n>1:
            raise(IpAddrException(f"no hay suficientes direcciones IP disponibles en la subred {network}"))
    return result
    

def parse_node(nodes:dict, compose:Compose, network:IPv4Network, *args, **conf) -> None:
    """
    Función "parse_node" que, para cada nodo, 
    parseará su contenido en el diccionario "compose"
    """
    compose["services"]={}
    ip_list = set()
    for node in nodes:
        case1, case2 = False, False
        replicas:int = 1
        
        if "build" in nodes[node]: case1=True
        if "image" in nodes[node]: case2=True


        if(case1 and case2) and node != "sniffer":
            raise ParseNodeException(f"El nodo {node} contiene cláusulas 'build':{nodes[node]['build']} e 'image':{nodes[node]['image']}")
        elif not(case1 or case2) and node != "sniffer":
            raise ParseNodeException("El nodo no contiene cláusulas 'build' ni 'image'")
        else:
            service:Service = {}
            service_replica:list[Service] = []

            if node == "sniffer": #Caso 0 : Nodo de monitorización
                service["image"] = "nicolaka/netshoot"
                service["cap_add"] = ["NET_ADMIN"]
                service["entrypoint"] = "/bin/bash /workspace/script_sniffer.sh"
                service ["volumes"]  = ["./:/workspace"]
                ip:IPv4Address = new_ip_addr(network, ip_list, 1)[0]
                ip_list.add(ip)
                service["networks"] = {list(compose["networks"])[0]:{"ipv4_address":f"{ip}"}}
                compose["services"][node] = service
                continue

            elif case1:   #Caso 1: contiene "build"
                service["build"] = nodes[node]["build"]
            elif case2: #Caso 2: contiene "image"
                service["image"] = nodes[node]["image"]

            service ["volumes"]  = ["./:/workspace"]
            if "needs" in nodes[node]:      service["depends_on"]   = nodes[node]["needs"]
            if "script" in nodes[node]:     service["entrypoint"]   = f'/bin/bash /workspace/{nodes[node]["script"]}'

            
            #########################################################################################################
            # Existen varias opciones posibles:
            #   1. El nodo está replicado y tiene una IP asignada -> ❌ ERROR
            #   2. El nodo está replicado y NO tiene una IP asignada:
            #       2.1. El nodo tiene una subred definida:
            #           2.1.1. La subred pertenece al rango del laboratorio ->     ✅ Se le asignan a los nodos IPs en dicho rango
            #           2.1.2. La subred NO pertenece al rango del laboratorio ->  ❌ ERROR
            #       2.2. El nodo no tiene una subred definida ->                   ✅ Se le asignan a los nodos IPs en el rango del laboratorio
            #   3. El nodo NO está replicado y tiene una IP asignada:
            #       3.1. La IP pertenece al rango del laboratorio:
            #           3.1.1. La IP está repetida ->                       ❌ ERROR
            #           3.1.2. La IP NO está repetida ->                    ✅ Se le asigna dicha IP
            #       3.2. La IP NO pertenece al rango del laboratorio ->     ❌ ERROR
            #   4. El nodo NO está replicado y NO tiene una IP asignada ->  ✅ Se le asigna una IP en el rango del laboratorio
            # A la hora de asignar direcciones IP, SIEMPRE se verificará que queden suficientes direcciones disponibles en el rango en cuestión,
            # en caso contrario, se lanzará una excepción.
            #########################################################################################################

            
            if "replicas" in nodes[node]:
                replicas = nodes[node]["replicas"] #Si tiene más de una réplica, se crean varios nodos similares
                for i in range(replicas):
                    service_replica.append(copy.deepcopy(service))
                #service["deploy"] = {"mode":"replicated", "replicas":nodes[node]["replicas"]}
            else:
                replicas = 1
            if "debug" in conf and conf["debug"]:print(f"{Fore.BLUE}\nEl nodo {node} tiene {replicas} réplica(s){Fore.RESET}")
            if replicas > 1:
                if "ip" in nodes[node]: # [1.]
                    raise ParseNodeException(f"No se puede replicar un nodo al que se le ha asignado IP: {node}")
                else: #[2.]
                    if "network" in nodes[node]: # [2.1.]
                        node_network:IPv4Network = ip_network(nodes[node]["network"])
                        if node_network.subnet_of(network): # [2.1.1.]
                            ips:list[IPv4Address] = new_ip_addr(node_network, ip_list, replicas)
                            for i in range(replicas):
                                ip_list.add(ips[i])
                                service_replica[i]["networks"] = {list(compose["networks"])[0]:{"ipv4_address":f"{ips[i]}"}}
                            

                        else: # [2.1.2.]
                            raise ParseNodeException(f"La subred {node_network} no pertenece a la red del laboratorio ({network})")

                    else: # [2.2.]
                        ips:list[IPv4Address] = new_ip_addr(network, ip_list, replicas)
                        for i in range(replicas):
                            ip_list.add(ips[i])
                            service_replica[i]["networks"] = {list(compose["networks"])[0]:{"ipv4_address":f"{ips[i]}"}}
                        

            elif "ip" in nodes[node]: # [3.]
                ip:IPv4Address = ip_address(nodes[node]["ip"])
                if ip in ip_list: # [3.1.1.]
                    raise ParseNodeException(f"La ip {ip} está repetida")
                elif not(ip in network): # [3.2.]
                    raise ParseNodeException(f"La ip {ip} no está contenida en el rango {network}")
                else: # [3.1.2.]
                    ip_list.add(ip)
                    service["networks"] = {list(compose["networks"])[0]:{"ipv4_address":f"{ip}"}}
            else: #[4.]
                
                ip:IPv4Address = new_ip_addr(network, ip_list, 1)[0]
                ip_list.add(ip)
                service["networks"] = {list(compose["networks"])[0]:{"ipv4_address":f"{ip}"}}
      

            
            
            if replicas==1:
                    compose["services"][node] = service
                    if "debug" in conf and conf["debug"]: 
                        print(f"{Fore.BLUE}\tservice '{node}':\n\t\t{service}{Fore.RESET}")
            else:
                for i in range(replicas): 
                    compose["services"][f"{node}_{i}"] = service_replica[i]
                    if "debug" in conf and conf["debug"]: 
                        print(f"{Fore.BLUE}\tservice '{node}_{i}':\n\t\t{service_replica[i]}{Fore.RESET}")

                
def read_output(proc) -> None:
    """
    Función 'read_output', que imprime por pantalla la salida estándar 
    de un subproceso y su código de retorno al finalizar.
    """
    for line in proc.stdout:
        print(line, end='')
    # espera a que el subproceso termine y obtiene su código de retorno
    return_code = proc.wait()
    # imprime el código de retorno del subproceso
    print(f"Código de retorno: {return_code}")


def stop_compose() -> None:
    with subprocess.Popen(shlex.split("docker compose stop"),
                                        stdout=subprocess.PIPE,
                                        universal_newlines=True) as p:
        t = Thread(target=read_output, args=(p,))
        t.start()


def read_monitor_output(proc:subprocess.Popen, content:list[list]) -> None:
    """
    Función read_monitor_output. Actualiza el contenido de una lista bidimensional 'content'
    con el output del proceso de monitorización 'proc' en un instante determinado.
    """
    header:bool = True
    result:list[list]=[]
    for line in proc.stdout:
        current_stats:list=["-","-","-","-","-","-","-","-"]
        if header:
            header = False
        else:
            split_line:list[str] = re.split(r'\s{2,}',line)
            if len(split_line) == 8:
                for i in range(len(split_line)):
                    current_stats[i]=split_line[i].strip()

            else:
                print("La línea contiene",len(split_line),"parámetros:")
                for i in split_line:
                    print("\t",i)
                print()
            result.append(current_stats)


    for i in range(len(content)):
        if i<len(result):
            content[i]=result[i]
        else:
            content[i]=["-","-","-","-","-","-","-","-"]

    return_code = proc.wait()
    # imprime el código de retorno del subproceso en caso de error
    if return_code != 0:
        print(f"Proceso 'read_monitor_output' finalizado con código: {Fore.RED}{return_code}{Fore.RESET}")
    else:
        print(f"{Fore.BLUE}Valores de monitorización refrescados{Fore.RESET}")


def itera_monitor_output(content:list[list]) -> None:
    """
    Función itera_monitor_output, que actualiza el contenido de una lista bidimensional 'content'
    con las estadísticas de los contenedores actualmente en ejecución en el equipo cada segundo.
    """
    while(True):
        process:subprocess.Popen = subprocess.Popen(shlex.split('docker stats --no-trunc --no-stream --format "table {{.ID}}\t{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}"'),
                                                stdout=subprocess.PIPE,
                                                universal_newlines=True)
        Thread(target=read_monitor_output, args=(process, content, )).start()
        time.sleep(1)


def interfaz_monitor(max_containers:int) -> None:
    """
    Función interfaz_monitor que mostrará la interfaz gráfica de monitorización del uso de recursos.
    Toma como único parámetro el número máximo de contenedores que monitorizar.
    """
    sg.theme('Default 1')
    content=[]
    for i in range(max_containers):
        content.append(["-","-","-","-","-","-","-","-"])

    Thread(target=itera_monitor_output, args=(content, ), daemon=True).start()
    

    layout = [[sg.Text('Monitorización de recursos'), sg.Text(text_color="red",key='-WARNING-')],
            [sg.Table(content, ["ID del Contenedor", "Nombre", "CPU %", "Memoria Utilizada", "Memoria %", "I/O de Red", "I/O de Bloque", "PIDs"], key="-TABLE-")],
            [sg.Button("Refrescar"), sg.Text("r", text_color="green"), sg.Text("ejecuta docker-compose en segundo plano,"), 
                                     sg.Text("s", text_color="red"), sg.Text("detiene la ejecución de los contenedores,"),
                                     sg.Text("esc", text_color="blue"), sg.Text("sale de la aplicación.")]
            ]
    window = sg.Window('Dockerlab - Resources', layout, icon="./Img/monitor_icon.png")

    while True: 
        
        event, values = window.read()
        
        if event == sg.WIN_CLOSED or event == 'Exit' or event == None:
            break
        window["-TABLE-"].update(content)
        if content[-1:][0] != ["-","-","-","-","-","-","-","-"]:
            window['-WARNING-'].update("ADVERTENCIA: algunos contenedores pueden no estar siendo mostrados")
        else:
            window["-WARNING-"].update("")
    window.close()

###############################
#      SCRIPT PRINCIPAL       #
###############################
def dockerlab(debug:bool=False,flags:Arguments={"build":True, "execute":True, "monitor":False, "execute":False}) -> None:
    #Caso por defecto
    if not(flags["build"]) and not(flags["execute"]) and not(flags["monitor"]) and not(flags["execute"]):
        flags["build"] = True
        flags["execute"] = True

    if flags["build"]:
        file = open("./config.yml", "r")
        compose_file = open("./docker-compose.yml", "w")
        config:dict = load (file, Loader=Loader)
        compose:Compose = {}
        compose["version"]="1.0.0"
        try:
            (network, nodes) = reader(config, compose, debug=debug)
            print("Se ha leído config.yml correctamente")
            if debug: print(f"{Fore.BLUE}\tNetwork:\t{network}\n\tNodes:\t{nodes}{Fore.RESET}")
            generate_network(network, compose, debug=debug)
            print("Red implementada correctamente.")
            if (flags["monitor"]):
                nodes["sniffer"] = {"":""}
            parse_node(nodes, compose, network, debug=debug)
            dump(compose, compose_file)
            print(f"{Fore.GREEN}'docker-compose.yml' generado correctamente.{Fore.RESET}")
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
    
    if flags["execute"]:
        # Hacemos pull y build
        print(f"{Fore.GREEN}Haciendo pull a los contenedores...{Fore.RESET}")
        read_output(subprocess.Popen(shlex.split("docker compose pull"),
                                    stdout=subprocess.PIPE,
                                    universal_newlines=True))
        print(f"{Fore.GREEN}¡Pull realizado correctamente!{Fore.RESET}")
        print(f"{Fore.GREEN}Construyendo contenedores...{Fore.RESET}")
        read_output(subprocess.Popen(shlex.split("docker compose build"),
                                    stdout=subprocess.PIPE,
                                    universal_newlines=True))
        print(f"{Fore.GREEN}¡Contenedores construidos satisfactoriamente!{Fore.RESET}")

        if flags["monitor"]:
            #TODO Ejecutar en modo "monitor"
            pass
        if flags["usage"]:
            Thread(target=interfaz_monitor, args=(len(compose["services"])+10,)).start()
            pass
        
        running:bool = False
        with keyboard.Events() as events:
            print(f"Pulse '{Fore.BLACK}{Back.WHITE}r{Fore.RESET}{Back.RESET}' para ejecutar docker-compose en segundo plano"+
                  f" y '{Fore.BLACK}{Back.WHITE}s{Fore.RESET}{Back.RESET}' para parar su ejecución."+
                  f" Para salir de la aplicación, pulse la tecla '{Fore.BLACK}{Back.WHITE}esc{Fore.RESET}{Back.RESET}'.")
            for event in events:
                if f'{event.key}' == "'r'" and not running:
                    print("Corriendo el subproceso 'docker-compose'...")
                    running = True

                    print("Creando subproceso docker-compose...")
                    process_compose:subprocess.Popen = subprocess.Popen(shlex.split("docker compose up"),
                                                    stdout=subprocess.PIPE,
                                                    universal_newlines=True)
                    print(f"{Fore.GREEN}Subproceso creado correctamente!{Fore.RESET}")
                    t = Thread(target=read_output, args=(process_compose,))
                    t.start()
                    
                    
                elif f'{event.key}' == "'s'" and running:
                    running = False #TODO: Si se pulsa antes de que empieze a ejecutar el docker-compose, se queda en un bucle infinito
                    print(f"{Fore.GREEN}Parando el subproceso...{Fore.RESET}")
                    stop_compose()

                elif event.key == keyboard.Key.esc:
                    if(running):
                        print(f"{Fore.GREEN}Parando el subproceso...{Fore.RESET}")
                        stop_compose()
                    break


        
    else:
        if flags["monitor"] or flags["usage"]:
            #TODO Imprimir mensaje de error, esta opción debe ir junto con "execute"
            pass


if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Herramienta para el despliegue de laboratorios virtuales mediante Docker. Por defecto, en caso de no proporcionar parámetros, se ejecutará con las banderas -be.")
    for i in [["-b", "--build",     "Indica que se desea generar el archivo docker-compose.yaml. Si sólo se selecciona esta opción, no se crearán los contenedores pertinentes."],
              ["-e", "--execute",   "Indica que se desean crear y levantar los contenedores definidos en docker-compose.yaml."],
              ["-m", "--monitor",   "Monitoriza el tráfico de paquetes en la red simulada. Debe usarse junto con -e."],
              ["-u", "--usage",     "Monitoriza el uso de recursos dentro de los contenedores de la simulación. Debe usarse junto con -e."]]:
        parser.add_argument(i[0],i[1], action='store_true', help=i[2])
    flags:Arguments = vars(parser.parse_args())
    dockerlab(debug=False, flags=flags)