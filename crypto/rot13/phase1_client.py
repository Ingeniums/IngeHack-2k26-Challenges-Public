#!/usr/bin/env python3
import argparse
import re
import socket
import ssl


def recv_until(sock: socket.socket, marker: bytes, timeout: float = 10.0) -> bytes:
    sock.settimeout(timeout)
    data = b""
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data


def send_line(sock: socket.socket, line: str) -> None:
    sock.sendall(line.encode() + b"\n")


def recv_available(sock: socket.socket, timeout: float = 2.0) -> bytes:
    sock.settimeout(timeout)
    data = b""
    while True:
        try:
            chunk = sock.recv(4096)
        except Exception:
            break
        if not chunk:
            break
        data += chunk
    return data


def parse_lcg_outputs(text: str) -> dict:
    matches = re.findall(r"x(\d+)\s*=\s*(\d+)", text)
    values = {f"x{idx}": int(val) for idx, val in matches}
    needed = {"x1", "x2", "x3", "x4"}
    if not needed.issubset(values.keys()):
        missing = sorted(needed - values.keys())
        raise ValueError(f"Missing LCG outputs in server response: {missing}")
    return values


def solve_phase1(outputs: dict) -> int:
    """Participant TODO: recover LCG multiplier a from four consecutive outputs.

    outputs keys: x1, x2, x3, x4
    """
    raise NotImplementedError("Implement solve_phase1(outputs) and return recovered a")


def create_socket(host: str, port: int, use_ssl: bool):
    raw_sock = socket.create_connection((host, port), timeout=10)
    if use_ssl:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context.wrap_socket(raw_sock, server_hostname=host)
    return raw_sock


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 1 client only: parse x1..x4, submit recovered a, then stop."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Challenge host")
    parser.add_argument("--port", type=int, default=4000, help="Challenge port")
    parser.add_argument("--ssl", action="store_true", help="Use SSL/TLS connection")
    args = parser.parse_args()

    with create_socket(args.host, args.port, args.ssl) as sock:
        phase1_data = recv_until(sock, b">> Recover a:")
        text = phase1_data.decode(errors="replace")
        print(text, end="")

        outputs = parse_lcg_outputs(text)
        print("\n[+] Parsed values:")
        print(f"    x1 = {outputs['x1']}")
        print(f"    x2 = {outputs['x2']}")
        print(f"    x3 = {outputs['x3']}")
        print(f"    x4 = {outputs['x4']}")

        recovered_a = solve_phase1(outputs)
        if not isinstance(recovered_a, int):
            raise TypeError("solve_phase1(outputs) must return int")

        print(f"\n[+] Auto-submitting recovered a: {recovered_a}")
        send_line(sock, str(recovered_a))

        feedback = recv_available(sock, timeout=2.0).decode(errors="replace")
        if feedback:
            print(feedback, end="")

        if "[+] Correct!" in feedback:
            print("\n[+] Phase 1 accepted.")
            print("[+] Please meet the organizer onsite to receive Phase 2 script.")
            return 0

        if "[-]" in feedback:
            print("\n[-] Phase 1 failed.")
            return 1

        print("\n[-] Unexpected server response.")
        return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[-] Interrupted by user")
        raise SystemExit(130)
