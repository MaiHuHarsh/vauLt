import os, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import load_dotenv


def GET_MASTER_KEY() -> bytes: 
    load_dotenv()
    return base64.b64decode(os.getenv("MASTER_KEY"))
    
def key_gen(length :int) -> bytes:
    if (length == 0): 
        length = 256
    return AESGCM.generate_key(bit_length=length)


def encrypt_text(text: str, key: bytes) -> bytes:

    if len(key) != 32:
        raise ValueError("Key must be exactly 32 bytes (256 bits)")

    nonce = os.urandom(12)
    aesgcm = AESGCM(key)

    ciphertext = aesgcm.encrypt(
        nonce,
        text.encode("utf-8"),
        None
    )

    return nonce + ciphertext


def encrypt_file(file_path: str, key: bytes) -> bytes:

    if len(key) != 32:
        raise ValueError("Key must be exactly 32 bytes (256 bits)")

    nonce = os.urandom(12)
    aesgcm = AESGCM(key)

    with open(file_path, "rb") as f:
        file_data = f.read()

    ciphertext = aesgcm.encrypt(
        nonce,
        file_data,
        None
    )

    return nonce + ciphertext



def decrypt_text(encrypted_data: bytes, key: bytes) -> str:

    if len(key) != 32:
        raise ValueError("Key must be exactly 32 bytes (256 bits)")

    if len(encrypted_data) < 28:
        raise ValueError("Invalid encrypted data")

    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]

    aesgcm = AESGCM(key)

    plaintext = aesgcm.decrypt(
        nonce,
        ciphertext,
        None
    )

    return plaintext.decode("utf-8")


def decrypt_file(encrypted_data: bytes, output_path: str, key: bytes):

    if len(key) != 32:
        raise ValueError("Key must be exactly 32 bytes (256 bits)")

    if len(encrypted_data) < 28:
        raise ValueError("Invalid encrypted data")

    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]

    aesgcm = AESGCM(key)

    plaintext = aesgcm.decrypt(
        nonce,
        ciphertext,
        None
    )

    with open(output_path, "wb") as f:
        f.write(plaintext)