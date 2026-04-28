import random

def encrypt():
    sbox = list(range(256))
    random.shuffle(sbox)
    k = random.randint(0, 255)

    try:
        with open('msg1.txt', 'r') as f:
            pt1 = f.read().lower().strip() 
            
        ct1 = bytes([sbox[ord(c)] ^ k for c in pt1])
        
        with open('ct1.txt', 'w') as f:
            f.write(ct1.hex())
            
    except FileNotFoundError:
        print("Error: msg1.txt not found")

    try:
        with open('msg2.txt', 'r') as f:
            pt2 = f.read().lower().strip()
            
        ct2 = bytes([sbox[ord(c)] ^ k for c in pt2])
        
        with open('ct2.txt', 'w') as f:
            f.write(ct2.hex())
            
    except FileNotFoundError:
        print("Error: msg2.txt not found")

if __name__ == "__main__":
    encrypt()
