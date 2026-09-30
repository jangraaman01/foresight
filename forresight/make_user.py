import os
from getpass import getpass
from src.auth import make_hash

password = getpass("Choose a password (typing is hidden): ")
salt = os.urandom(16).hex()
print()
print("Copy the line below into secrets.toml:")
print(salt + "$" + make_hash(password, salt))