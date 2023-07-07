#
# Author: Meyer Pidiache <meyer.pidiache@gmail.com>
# Co-Authors: ChatGTP 3.5, Debugcode.ai
#

from decouple import config as getenv
import string, os
from time import sleep
import concurrent.futures, requests
import psycopg2

# Constants
PRODUCTION = getenv("PRODUCTION")
CHARACTERS = string.ascii_letters + string.digits
SHORTURL_DOMAINS = {
    "https://t.ly/": 4,
    "https://rb.gy/": 5,
    "https://www.shorturl.at/": 5,
    "https://tinyurl.com/": 6,
}

# Database
conn = psycopg2.connect(
    user=getenv("user"),
    password=getenv("password"),
    host=getenv("host"),
    port=getenv("port"),
    database=getenv("database"),
)
cursor = conn.cursor()

cursor.execute(
    """ CREATE TABLE if NOT EXISTS base_1 (
            id VARCHAR(10) PRIMARY KEY NOT NULL,
            redirect_url TEXT,
            creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
)

conn.commit()


def start_process(characters: str, domain_option: int) -> None:
    global indices
    global path
    num_characters = len(characters)

    # Cargar la longitud del dominio y el dominio a usar
    domain_length = list(SHORTURL_DOMAINS.values())[domain_option]
    domain = list(SHORTURL_DOMAINS.keys())[domain_option]

    # Recuperar la lista de índices de la base de datos
    cursor.execute("SELECT COUNT(*) FROM base_1")
    result = cursor.fetchone()
    if result[0] > 0:
        indices = load_state()
        print(f"Retomando ejecución desde {indices}\n")
    else:
        # Lista de índices base
        indices = [0] * domain_length

    # Executor
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

    # Generar las permutaciones iterativamente
    futures = []
    iter = int()
    while True:
        iter += 1
        # Permutación actual usando el arreglo de índices y la lista de caracteres
        path = "".join([characters[i] for i in indices])

        # Crear una lista vacía para almacenar los futuros (tareas) que enviaremos al executor

        # Enviar una tarea al executor para verificar si la URL corta formada por el dominio y la ruta está disponible
        futures.append(executor.submit(get_url_available, domain, path))
        # Encontrar el siguiente índice a incrementar
        i = domain_length - 1

        # Mientras los números a la derecha sean los máximos, moverse a la izquierda
        while i >= 0 and indices[i] == num_characters - 1:
            i -= 1

        # Si todos los índices han alcanzado el máximo, terminar el bucle
        if i < 0:
            break

        # Incrementar el índice encontrado y ajustar los siguientes índices de la derecha a 0
        indices[i] += 1

        for j in range(i + 1, domain_length):
            indices[j] = 0

    # Cerrar el executor después de terminar el procesamiento
    executor.shutdown()


def get_url_available(domain, path):
    """Comprueba si una URL corta está disponible."""
    try:
        url = domain + path
        response = requests.get(url, timeout=5)
        response.encoding = "utf-8"
        status_code = response.status_code

        if response.history and response.url != domain and not 400 <= status_code < 500:
            result = response.url
            if path != id_state:
                print(f"({response.status_code}) {url} -> {result}\n")
                cursor.execute(
                    """
                    INSERT INTO base_1 (id, redirect_url)
                    VALUES (%s, %s)
                """,
                    (path, result[8:]),
                )
                conn.commit()

    except requests.exceptions.RequestException as e:
        print("Error (get_url_available): ", e)


def id_exist(id: str) -> bool:
    cursor.execute("SELECT EXISTS(SELECT id FROM base_1 WHERE id=%s);", (id,))

    return cursor.fetchone()[0]


# Función para guardar el estado en un archivo
def save_state() -> None:
    conn.rollback()

    if not id_exist(path):
        cursor.execute("INSERT INTO base_1 (id) VALUES (%s)", (path,))
        conn.commit()


# Función para cargar el estado desde un archivo
def load_state() -> list:
    global id_state
    cursor.execute("SELECT id FROM base_1 ORDER BY creation_date DESC LIMIT 1")
    result = cursor.fetchone()
    id_state = result[0]
    # Retorna una lista de los índices de los caracteres
    return [CHARACTERS.index(i) for i in id_state]


def main() -> None:
    global domain_option

    if PRODUCTION:
        domain_option = 0
        start_process(CHARACTERS, domain_option)
    else:
        # Seleccionar un dominio
        counter = 1

        for key in SHORTURL_DOMAINS.keys():
            print(f"{counter}. {key}")
            counter += 1

        domain_option = int(input("\nIngrese una opción (1 - 5): ")) - 1
        print()

        start_process(CHARACTERS, domain_option)

if __name__ == "__main__":
    main()

