# Herramienta para despliegue de laboratorios virtuales mediante Docker
El presente repositorio muestra una herramienta para automatizar el despliegue de laboratorios virtuales mediante Docker.
Se trata de un Trabajo de Fin de Grado (TFG) desarrollado en el curso 2022/23 para el Grado en Ingeniería de las Tecnologías de Telecomunicación de la Universidad de Sevilla.
## Funcionamiento
Una vez descargado el repositorio, se introducirá en la carpeta contenedora del archivo "dockerlab.py" un script llamado "config.yml" en formato YAML, el cual contendrá las especificaciones del laboratorio virtual a desplegar. Actualmente, el archivo debe tener la siguiente estructura:
- `<lab_name>`: nombre del laboratorio (en el ejemplo, `lab`).
  - `network`: dirección IPv4 que indica la subred del laboratorio.
  - `nodes`: lista de nodos que componen el laboratorio.
    - `<node_name>`: nombre del nodo en cuestión.
      - `image`: imagen en la que se va a basar el nodo. Es excluyente con la funcionalidad `build`.
      - `build`: en caso de querer basar un nodo en un contenedor definido por el usuario, se incluirá una carpeta en el directorio actual que contenga los archivos necesarios para su despliegue y se indicará en esta directiva su nombre. Es excluyente con la funcionalidad `image`.
      - `script`: en caso de querer que se ejecute un shell-script en el contenedor a desplegar cuando este se inicie, se debe indicar aquí su nombre tal y como esté almacenado en el directorio actual.
      - `network`: si deseamos que se le asigne una dirección IP en un subrango de la red del laboratorio, se indicará en esta directiva. Es excluyente con la funcionalidad `ip`.
      - `ip`: si deseamos que al nodo actual se le despliegue con una dirección IP concreta dentro del rango de la red del laboratorio, se indicará en esta directiva. Es excluyente con las funcionalidades `network` y `replicas`.
      - `replicas`: en caso de desear desplegar varios contenedores con configuraciones similares, se indicará en esta directiva el número de instancias a desplegar. Es incompatible con la funcionalidad `ip` sólo en caso de que su valor sea superior a "1". Cada réplica tendrá una variable de entorno `$REPLICA_ID` con un identificador que ayude a diferenciarla de las demás (un valor entre 0 y el número máximo de réplicas - sin incluir este último).
      - `needs`: lista de dependencias para el despliegue del contenedor. Sirve para generar un orden de despliegue personalizado.
## Ejecución
Se puede indicar el modo de ejecución deseado para `dockerlab.py` a modo de banderas en sus argumentos:
- `-b` o `--build`: Indica que se desea generar el archivo `docker-compose.yml`. Si sólo se selecciona esta opción, no se crearán los contenedores pertinentes.
- `-e` o `--execute`: Indica que se desean crear y levantar los contenedores definidos en `docker-compose.yml`.
- `-m` o `--monitor`: Monitoriza el tráfico de paquetes en la red simulada. Debe usarse junto con `-e`.
- `-u` o `--usage`: Monitoriza el uso de recursos dentro de los contenedores de la simulación. Debe usarse junto con `-e`.

Por defecto, en caso de no proporcionar parámetros, se ejecutará con las banderas `-be`.
Una vez el archivo `docker-compose.yml` haya sido creado, se proporcionará la opción de correr la simulación pulsando la tecla `r` y de pararla pulsando la tecla `s`. Para salir de la aplicación, se debe pulsar la tecla `esc`.
## Dependencias 
Para la ejecución del presente software se deben cumplir los siguientes requisitos:
- Docker 23.0.3 o posteriores[^1]
- Docker-compose 1.29.2 o posteriores[^1]
- Python 3.10.6 o posteriores[^1]
- Librerías contenidas en el archivo `requirements.txt`.

Para la instalación de dependencias se muestra a continuación el proceso a seguir en un equipo con una distribución de Linux basada en Debian (se han de realizar las siguientes acciones con permisos de superusuario):
1. Se actualiza la lista de repositorios y los paquetes actualmente instalados:
```bash
apt update
apt upgrade
```
2. Haciendo uso del gestor de paquetes, se instalan las últimas versiones del software necesario:
```bash
apt install docker
apt install docker-compose
apt install python3
apt install python3-tk
```
3. Para instalar las librerías necesarias, situarse en la carpeta contenedora del archivo `requirements.txt` y ejecutar la orden:
```bash
python3 -m pip install -r requirements.txt
```

## Errores conocidos
- A la hora de ejecutar el programa por primera vez, es posible que aparezca el error `Got permission denied while trying to connect to the Docker daemon socket`, esto es debido a que el usuario desde el que se está ejecutando la aplicación no pertenece al grupo `docker`. Para solucionarlo, primero habrá que crear dicho grupo con `sudo groupadd docker`. A continuación, habrá que añadir al usuario a dicho grupo mediante la orden `sudo usermod -aG docker ${USER}`. Posteriormente, habrá que volver a iniciar la sesión de dicho usuario mediante `su - ${USER}`. Para comprobar que todo funcione correctamente, se pueded ejecutar el comando `docker run hello-world`.
- Si a la hora de parar la ejecución se recibe un error `Error while Stopping` y los contenedores continúan con su ejecución, puede deberse al uso de AppArmor (módulo de seguridad del kernel Linux que permite al administrador del sistema restringir las capacidades de un programa). Para solucionar el problema, abrir una nueva terminal y escribir `sudo aa-remove-unknown`[^2]. Una vez ejecutado, escribir `docker compose down`, el problema debería solucionarse de esta forma.

[^1]: Se ha probado el correcto funcionamiento del presente repositorio con las versiones indicadas de las dependencias, por lo que, aunque puede que funcione correctamente con algunas versiones anteriores, sólo se puede garantizar que no se van a encontrar problemas inesperados con las versiones aquí indicadas.
[^2]: Pueden encontrarse múltiples procesos "snap.docker.dockerd" en el output de `aa-status`, y la forma de eliminarlos y poder parar los contenedores de docker es mediante la orden `aa-remove-unknown`. Información consultada en el siguiente enlace: [https://javahowtos.com/guides/124-docker/414-solved-cannot-kill-docker-container-permission-denied.html](https://javahowtos.com/guides/124-docker/414-solved-cannot-kill-docker-container-permission-denied.html)
