import base64
import hashlib
#import secrets  # no, is python3.6
from random import SystemRandom
import pkg_resources
import io

stream = io.TextIOWrapper(pkg_resources.resource_stream(__package__,'words.txt'))
try:
    all_words = [line.strip() for line in stream.readlines()]
finally:
    stream.close()

def randomwords(k=4):
    return [SystemRandom().choice(all_words) for _ in range(k)]

def hashwords_b64(words):
    msg = ' '.join(words).encode()
    digest = hashlib.sha256(msg).digest()
    b64_bytes = base64.urlsafe_b64encode(digest)
    return str(b64_bytes,'utf-8').rstrip('=')

def hashwords_hex(words):
    msg = ' '.join(words).encode()
    return hashlib.sha256(msg).hexdigest()

def id_hash(words):
    return hashwords_b64(words)[:8]