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


def recv_available(sock: socket.socket, timeout: float = 0.5) -> bytes:
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


def parse_commitments(text: str) -> list[dict]:
    blocks = re.findall(
        r"\[(\d+)\]\s*k_\d+\s*=\s*(\d+)\s*\n\s*Q_\d+\s*=\s*\((\d+)\s*:\s*(\d+)\s*:\s*(\d+)\)\s*\n\s*SHA256\(P_\d+\.x\)\s*=\s*([0-9a-f]{64})",
        text,
        flags=re.MULTILINE,
    )
    commitments = []
    for idx, k, qx, qy, qz, digest in blocks:
        commitments.append(
            {
                "index": int(idx),
                "k": int(k),
                "Q": {"x": int(qx), "y": int(qy), "z": int(qz)},
                "sha256_px": digest,
            }
        )
    commitments.sort(key=lambda item: item["index"])
    if not commitments:
        raise ValueError("No commitments found in server response.")
    return commitments


def solve_phase1(outputs: dict) -> int:
    """Participant TODO: recover LCG multiplier a from outputs and return int."""
    raise NotImplementedError("Implement solve_phase1(outputs) and return recovered a")


def solve_commitments(commitments: list[dict]) -> dict[int, int]:
    """Participant TODO: return mapping {index: recovered_Px_int}."""
    raise NotImplementedError("Implement solve_commitments(commitments)")


def build_final_submission() -> str:
    """Participant TODO: return final Phase 3 submit string."""
    raise NotImplementedError("Implement build_final_submission()")


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
        description="Phase 2 interaction client. No solver logic included."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Challenge host")
    parser.add_argument("--port", type=int, default=4000, help="Challenge port")
    parser.add_argument("--ssl", action="store_true", help="Use SSL/TLS connection")
    args = parser.parse_args()

    with create_socket(args.host, args.port, args.ssl) as sock:
        phase1_data = recv_until(sock, b">> Recover a:")
        phase1_text = phase1_data.decode(errors="replace")
        print(phase1_text, end="")

        outputs = parse_lcg_outputs(phase1_text)
        recovered_a = solve_phase1(outputs)
        if not isinstance(recovered_a, int):
            raise TypeError("solve_phase1(outputs) must return int")

        print(f"\n[+] Auto-submitting recovered a: {recovered_a}")
        send_line(sock, str(recovered_a))

        phase2_data = recv_until(sock, b"Now recover P_i.x for each commitment.")
        text = phase2_data.decode(errors="replace")
        print(text, end="")

        if "[-]" in text:
            print("\n[-] Wrong or invalid a. Ask organizer for Phase 2 access again.")
            return 1

        commitments = parse_commitments(text)
        print(f"\n[+] Parsed {len(commitments)} commitments.")

        recovered_px = solve_commitments(commitments)
        if not isinstance(recovered_px, dict):
            raise TypeError("solve_commitments(commitments) must return dict[int, int]")

        for pos, item in enumerate(commitments):
            prompt = recv_available(sock, timeout=0.4).decode(errors="replace")
            if prompt:
                print(prompt, end="")
            idx = item["index"]
            if idx not in recovered_px:
                raise KeyError(f"Missing recovered P_{idx}.x in solve_commitments output")
            px = recovered_px[idx]
            if not isinstance(px, int):
                raise TypeError(f"Recovered P_{idx}.x must be int")
            print(f"[+] Auto-submitting P_{idx}.x = {px}")
            send_line(sock, str(px))

            if pos == len(commitments) - 1:
                next_marker = b">> Submit:"
            else:
                next_idx = commitments[pos + 1]["index"]
                next_marker = f">> P_{next_idx}.x :".encode()

            feedback = recv_until(sock, next_marker, timeout=10)
            msg = feedback.decode(errors="replace")
            print(msg, end="")
            if "[-]" in msg:
                return 1

        final_answer = build_final_submission()
        if not isinstance(final_answer, str):
            raise TypeError("build_final_submission() must return str")
        print(f"[+] Auto-submitting final answer: {final_answer}")
        send_line(sock, final_answer)

        sock.settimeout(1.0)
        output = b""
        while True:
            try:
                chunk = sock.recv(4096)
            except Exception:
                break
            if not chunk:
                break
            output += chunk

        print(output.decode(errors="replace"), end="")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[-] Interrupted by user")
        raise SystemExit(130)
