# PasswordHash imported from the correct library.
from pwdlib import PasswordHash 

# PasswordHash.recommended() creates a recommended password-hashing configuration.
password_hasher= PasswordHash.recommended()

def hash_password(password:str) -> str: 
    return password_hasher.hash(password) # .hash() hashes the supplied password.

def verify_password(password:str, hashed_password:str) -> bool:
    return password_hasher.verify(password, hashed_password) # .verify() checks if a password matches the hash.