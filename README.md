# Herramienta para despliegue de laboratorios virtuales mediante Docker
El presente repositorio muestra una herramienta para automatizar el despliegue de laboratorios virtuales mediante Docker.
Se trata de un Trabajo de Fin de Grado (TFG) desarrollado en el curso 2022/23 para el Grado en Ingeniera de las Tecnologías de Telecomunicación de la Universidad de Sevilla.
## Funcionamiento
Una vez descargado el repositorio, se introducirá en la carpeta contenedora del archivo "dockerlab.py" un script llamado "config.yml" en formato YAML, el cual contendrá las especificaciones del laboratorio virtual a desplegar. Actualmente, el archivo debe tener la siguiente estructura:
- `<lab_name>`: nombre del laboratorio (en el ejemplo, `lab`).
  - `network`: dirección IPv4 que indica la subred del laboratorio.
  - `nodes`: lista de nodos que componen el laboratorio.
    - `<node_name>`: nombre del nodo en cuestión.
      - `image`: imagen en la que se va a basar el nodo. Es excluyente con la funcionalidad `build`.
      - `build`: en caso de querer basar un nodo en un contenedor definido por el usuario, se incluirá una carpeta en el directorio actual que contenga los archivos necesarios para su despliegue y se indicará en esta directiva su nombre. Es excluyente con la funcionalidad `image`.
      - `script`: en caso de querer que se introduzca un script en el contenedor a desplegar, se debe indicar aquí su nombre tal y como esté almacenado en el directorio actual.
      - `network`: si deseamos que se le asigne una dirección IP en un subrango de la red del laboratorio, se indicará en esta directiva. Es excluyente con la funcionalidad `ip`.
      - `ip`: si deseamos que al nodo actual se le despliegue con una dirección IP concreta dentro del rango de la red del laboratorio, se indicará en esta directiva. Es excluyente con las funcionalidades `network` y `replicas`.
      - `replicas`: en caso de desear desplegar varios contenedores con configuraciones similares, se indicará en esta directiva el número de instancias a desplegar. Es incompatible con la funcionalidad `ip` sólo en caso de que su valor sea superior a "1".
      - `needs`: lista de dependencias para el despliegue del contenedor. Sirve para generar un orden de despliegue personalizado.
