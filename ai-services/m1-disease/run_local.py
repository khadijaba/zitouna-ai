"""Lance l'API M1 en local sur IPv4 ET IPv6 simultanément.

Pourquoi : sur Windows, la JVM du backend Spring résout « localhost » en ::1 (IPv6)
ou en 127.0.0.1 (IPv4) selon la configuration. `uvicorn --host 127.0.0.1` ne couvre
que l'IPv4 et `--host ::` ne couvre que l'IPv6 sur cette machine — l'un des deux
donnait « Connection refused » côté backend (erreur 500 sur /api/ai/disease).
Ce lanceur ouvre les deux sockets dans un seul processus (un seul modèle en RAM).

Usage (depuis ai-services/m1-disease, venv activé) :

    python run_local.py            # port 8001 sur 127.0.0.1 + [::1]

En Docker, inutile : le Dockerfile utilise uvicorn classique et le réseau compose
résout les noms de services en IPv4.
"""

import socket

import uvicorn

from app.main import app

PORT = 8001


def _listen(family: int, address: tuple) -> socket.socket:
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if family == socket.AF_INET6:
        # v6only explicite : on ouvre ::1 SEUL en IPv6, l'IPv4 a son propre socket
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
    sock.bind(address)
    sock.listen(2048)
    sock.set_inheritable(True)
    return sock


if __name__ == "__main__":
    sockets = [
        _listen(socket.AF_INET, ("0.0.0.0", PORT)),
        _listen(socket.AF_INET6, ("::1", PORT)),
    ]
    print(f"M1 en écoute sur 127.0.0.1:{PORT} (IPv4) et [::1]:{PORT} (IPv6)")
    uvicorn.Server(uvicorn.Config(app, log_level="info")).run(sockets=sockets)
