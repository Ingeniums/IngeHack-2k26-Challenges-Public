#!/usr/bin/env python3

import argparse
import re
import select
import socket
import ssl
import time
from dataclasses import dataclass


@dataclass
class Stage1Data:
    n0: int
    n1: int
    n2: int
    c: int
    e: int
    lambda1_bits: int
    lambda2_bits: int


class Remote:
    def __init__(self, host: str, port: int, use_ssl: bool = False, verify_cert: bool = True):
        raw_sock = socket.create_connection((host, port))

        if use_ssl:
            ctx = ssl.create_default_context()
            if not verify_cert:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            self.sock = ctx.wrap_socket(raw_sock, server_hostname=host)
        else:
            self.sock = raw_sock

        self.sock.setblocking(False)
        self.buf = b""

    def recv_until(self, marker: bytes, timeout: float = 30.0) -> bytes:
        deadline = time.monotonic() + timeout
        while marker not in self.buf:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"Timed out waiting for marker: {marker!r}\n"
                    + self.buf.decode(errors="ignore")
                )
            ready, _, _ = select.select([self.sock], [], [], remaining)
            if not ready:
                continue
            try:
                chunk = self.sock.recv(4096)
            except ssl.SSLWantReadError:
                continue
            if not chunk:
                raise ConnectionError(
                    "Connection closed while waiting for protocol marker.\n"
                    + self.buf.decode(errors="ignore")
                )
            self.buf += chunk

        idx = self.buf.index(marker) + len(marker)
        out = self.buf[:idx]
        self.buf = self.buf[idx:]
        return out

    def recv_until_any(self, markers: list[bytes], timeout: float = 30.0) -> tuple[bytes, bytes]:
        deadline = time.monotonic() + timeout
        while True:
            for marker in markers:
                if marker in self.buf:
                    idx = self.buf.index(marker) + len(marker)
                    out = self.buf[:idx]
                    self.buf = self.buf[idx:]
                    return out, marker

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    "Timed out waiting for protocol marker.\n"
                    + self.buf.decode(errors="ignore")
                )
            ready, _, _ = select.select([self.sock], [], [], remaining)
            if not ready:
                continue
            try:
                chunk = self.sock.recv(4096)
            except ssl.SSLWantReadError:
                continue
            if not chunk:
                raise ConnectionError(
                    "Connection closed while waiting for protocol marker.\n"
                    + self.buf.decode(errors="ignore")
                )
            self.buf += chunk

    def send_line(self, data: bytes) -> None:
        self.sock.sendall(data + b"\n")

    def close(self) -> None:
        self.sock.close()


def parse_stage1(block: str) -> Stage1Data:
    n0 = int(re.search(r"N_0\s*=\s*(\d+)", block).group(1))
    n1 = int(re.search(r"N_1\s*=\s*(\d+)", block).group(1))
    n2 = int(re.search(r"N_2\s*=\s*(\d+)", block).group(1))
    c = int(re.search(r"c\s*=\s*(\d+)", block).group(1))
    e_match = re.search(r"e\s*=\s*(\d+)", block)
    e = int(e_match.group(1)) if e_match else 65537
    b1 = int(re.search(r"size\(λ1\)\s*=\s*(\d+)\s*bits", block).group(1))
    b2 = int(re.search(r"size\(λ2\)\s*=\s*(\d+)\s*bits", block).group(1))
    return Stage1Data(n0=n0, n1=n1, n2=n2, c=c, e=e, lambda1_bits=b1, lambda2_bits=b2)


def solve_stage1(stage1: Stage1Data) -> bytes:
    raise NotImplementedError("TODO: return the exact plaintext bytes for Stage 1")


def run(host: str, port: int, use_ssl: bool = False, verify_cert: bool = True) -> None:
    io = Remote(host, port, use_ssl=use_ssl, verify_cert=verify_cert)
    try:
        stage1_block = io.recv_until(b"Decrypt the message >> ").decode(errors="ignore")
        stage1 = parse_stage1(stage1_block)

        answer = solve_stage1(stage1)
        if not isinstance(answer, (bytes, bytearray)):
            raise TypeError("solve_stage1 must return bytes")

        io.send_line(bytes(answer).strip())

        response, marker = io.recv_until_any([b"Enter phrase:", b"[-] Wrong."], timeout=30.0)
        text = response.decode(errors="ignore")
        print(text)

        if marker == b"Enter phrase:":
            print("[+] Phase 1 solved. Stop here and hand off to onsite for Phase 2.")
        else:
            print("[-] Stage 1 answer rejected.")
    finally:
        io.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 1 player client template")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default=4000, type=int)
    parser.add_argument(
        "--ssl",
        action="store_true",
        help="Wrap the connection in SSL/TLS",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Disable SSL certificate verification (useful for self-signed certs)",
    )
    args = parser.parse_args()
    run(args.host, args.port, use_ssl=args.ssl, verify_cert=not args.no_verify)


if __name__ == "__main__":
    main()
