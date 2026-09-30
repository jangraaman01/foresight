import tomllib
from getpass import getpass
from src.auth import make_hash

with open(".streamlit/secrets.toml", "rb") as f:
    users = tomllib.load(f).get("users", {})

print("Users found:", list(users.keys()))

name = input("Username: ").strip()
stored = users.get(name)
if not stored:
    print("-> That username is not in secrets.toml (names are case-sensitive).")
    raise SystemExit

print("Stored value length:", len(stored), "(should be 32 + 1 + 64 = 97)")
if "$" not in stored:
    print("-> The stored value has no '$'. The hash was copied incorrectly.")
    raise SystemExit

salt, expected = stored.split("$", 1)
pw = getpass("Password: ")
print("-> MATCH" if make_hash(pw, salt) == expected else "-> Password does NOT match this hash")