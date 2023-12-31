import socket
import json

"""
@   Archivo principal de servicio
*   Todos los servicios que se creen deberán importar las funciones necesarias de este archivo.
"""


def send_message(sock, message):
    """
    @   Enviar mensaje al socket
    *   Se asume que el mensaje fue codificado previamente a enviar usando incode_response
    """
    sock.sendall(message)


def receive_message(sock, expected_length):
    """
    @   Recibir mensaje
    *   Calcula el tamaño del mensaje de acuerdo al bus y lee los datos
    """
    received_data = b''
    while len(received_data) < expected_length:
        data = sock.recv(expected_length - len(received_data))
        if not data:
            raise RuntimeError("Socket connection closed prematurely.")
        received_data += data
    return received_data


def decode_response(response):
    """
    @   Decodificar mensajes de los clientes
    *   Por alguna razón hay veces donde se envía con el largo del mensaje y otras veces que no.
    *   Por tanto se revisa esos casos y se retorna un diccionario con 'length', 'status' y 'data'
    *   Data corresponde al JSON que envía el cliente.
    """
    response = response.decode('utf-8')
    try:
        length = int(response[:5])
        service = response[5:10]
        response_data = json.loads(response[10:])
        if response[5:7] == 'OK' or response[5:7] == 'NK':
            service = response[7:12]
            response_data = json.loads(response[12:])
        return {
            "length": length,
            "service": service,
            "data": response_data
        }
    except ValueError:
        service = response[:5]
        response_data = json.loads(response[5:])
        if response[5:7] == 'OK' or response[5:7] == 'NK':
            service = response[7:12]
            response_data = json.loads(response[12:])
        return {
            "length": 0,
            "service": service,
            "data": response_data
        }


def incode_response(service, response):
    """
    @   Codificar mensaje hacia el cliente
    *   Enviamos un JSON codificado en bytes que sigue el patrón de mensaje del bus.
    """
    data_json = json.dumps(response)
    msg_len = len(service) + len(data_json)
    response_formatted = f'{msg_len:05d}{service}{data_json}'
    return response_formatted.encode('utf-8')


def is_sinit_response(response):
    """
    @   Revisamos respuesta de SInit
    *   Esto es para poder saltar un mensaje adicional que no era necesario.
    """
    response = response.decode('utf-8')
    if response[:5] == 'sinit':
        return True
    return False


def main_service(service, process_request):
    """
    @   Servicio principal
    *   Todos los servicios deben tener esta función para ser servicio. Se conecta al bus en localhost y puerto 5000.
    *   Envia un mensaje de 'sinit' para poder iniciar el servicio dentro del bus.
    *   Luego, se queda en un loop infinito esperando transacciones.
    *   Cuando llega una transaccion, es procesada por la función 'process_request' de cada servicio.
    *   El resultado del procesamiento lo decodificamos para posteriormente codificarlo y enviarlo.
    """
    server_address = ('localhost', 5000)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect(server_address)

            message = bytes(f'00010sinit{service}', 'utf-8')
            print(f'Sending message: {message}')
            send_message(sock, message)

            while True:
                print('Waiting for transaction...')
                expected_length = int(receive_message(sock, 5).decode('utf-8'))
                data = receive_message(sock, expected_length)
                print(f'Received data: {data}')

                if is_sinit_response(data):
                    continue

                print('Processing...')
                response = process_request(sock, data)
                decoded = decode_response(response)
                response = incode_response(decoded['service'], decoded['data'])
                print(f'Sending response: {response}')
                send_message(sock, response)
        except KeyboardInterrupt:
            print(f'Terminating service {service}')
        finally:
            sock.close()
