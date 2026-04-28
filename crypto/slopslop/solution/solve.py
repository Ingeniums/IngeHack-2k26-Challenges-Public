import collections

def map_messages():
    ct1_bytes = b""
    ct2_bytes = b""
    
    try:
        with open('../dist/ct1.txt', 'r') as f:
            ct1_bytes = bytes.fromhex(f.read().strip())
    except FileNotFoundError:
        pass

    try:
        with open('../dist/ct2.txt', 'r') as f:
            ct2_bytes = bytes.fromhex(f.read().strip())
    except FileNotFoundError:
        pass

    combined_bytes = ct1_bytes + ct2_bytes

    if not combined_bytes:
        return "Error: No ciphertext files found."

    counts = collections.Counter(combined_bytes)
    unique_bytes = [item[0] for item in counts.most_common()]
    
    placeholders = " abcdefghijklmnopqrstuvwxyz"
    
    byte_to_char = {}
    for i, b in enumerate(unique_bytes):
        if i < len(placeholders):
            byte_to_char[b] = placeholders[i]
        else:
            byte_to_char[b] = "?"

    mapped_text1 = "".join(byte_to_char[b] for b in ct1_bytes)
    mapped_text2 = "".join(byte_to_char[b] for b in ct2_bytes)
    
    return mapped_text1 + "   " + mapped_text2

if __name__ == "__main__":
    result = map_messages()
    print(result)
