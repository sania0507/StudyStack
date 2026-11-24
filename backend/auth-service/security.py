# PasswordHash imported from the correct library.
from pwdlib import PasswordHash 

# PasswordHash.recommended() creates a recommended password-hashing configuration.
password_hasher= PasswordHash.recommended()

def hash_password(password:str) -> str: 
    return password_hasher.hash(password) # .hash() hashes the supplied password.

def verify_password(password:str, hashed_password:str) -> bool:
    return password_hasher.verify(password, hashed_password) # .verify() checks if a password matches the hash.

# ---- refresh tokens -------------------------------------------------------
#
# A refresh token is a bearer credential, so only its hash is stored: a leaked
# database dump then yields nothing usable. SHA-256 is the right choice here
# and Argon2 is the wrong one - the token is 256 bits of randomness, so there
# is nothing to brute force, and every refresh needs a fast lookup.

import hashlib
import secrets

REFRESH_TOKEN_BYTES = 48


def new_refresh_token() -> str:
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
