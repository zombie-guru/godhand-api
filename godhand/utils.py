from itertools import islice
from urllib.parse import urlparse
import socket
import time


def socket_is_open(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def wait_for_socket_open(host, port):
    for _ in range(10):
        if socket_is_open(host, port):
            return
        time.sleep(1)
    raise RuntimeError('Timeout when waiting for {}:{}'.format(host, port))


def wait_for_couchdb(url):
    url = urlparse(url)
    wait_for_socket_open(url.hostname, url.port)


def batched(gen, batch_size):
    gen = iter(gen)
    while True:
        batch = list(islice(gen, 0, batch_size))
        if len(batch) > 0:
            yield batch
        if len(batch) < batch_size:
            return
