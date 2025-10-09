import ast
import copy
from cryptography.fernet import Fernet
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import secrets
import uuid

backend = default_backend()
iterations = 100_000

def derive_key(password: bytes, salt: bytes) -> bytes:
    """Derive a secret key from a given password and salt"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), 
        length=32, 
        salt=salt,
        iterations=iterations, 
        backend=default_backend())
    return base64.urlsafe_b64encode(kdf.derive(password))

def password_encrypt(text: str, password: str) -> bytes:
    salt = secrets.token_bytes(16) # Generate a salt
    key = derive_key(password.encode(), salt) #enccode password as utf, send it to derive key, which generates a password in non base64, encodes it as b64 and returns it
    encoded = text.encode()
    return base64.urlsafe_b64encode(
        b'%b%b%b' % (
            salt,
            iterations.to_bytes(4, 'big'),
            base64.urlsafe_b64decode(Fernet(key).encrypt(encoded)),
        )
    )

def password_decrypt(encrypted_data: bytes, password: str) -> str:
    decoded = base64.urlsafe_b64decode(encrypted_data) # returns non base64 bytes
    salt, iter, encrypted_txt = decoded[:16], decoded[16:20], base64.urlsafe_b64encode(decoded[20:])
    iterations = int.from_bytes(iter, 'big')
    key = derive_key(password.encode(), salt)
    return Fernet(key).decrypt(encrypted_txt).decode()