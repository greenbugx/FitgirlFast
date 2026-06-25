import base64
import zlib
import json
import requests

BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def base58_decode(s):
    num = 0
    for char in s:
        if char not in BASE58_ALPHABET:
            raise ValueError(f"Invalid base58 char: {char}")
        num = num * 58 + BASE58_ALPHABET.index(char)
    return num.to_bytes((num.bit_length() + 7) // 8, 'big') if num else b'\x00'

def _pad_b64(s):
    return s + '=' * (-len(s) % 4)

def decrypt_privatebin_v2(paste_data, key_str):
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key_bytes = base58_decode(key_str)
    adata     = paste_data['adata']
    ct_b64    = paste_data['ct']

    iv_b64, salt_b64, iterations, keylen_bits = adata[0][:4]
    compression = adata[0][7] if len(adata[0]) > 7 else 'zlib'

    iv   = base64.b64decode(_pad_b64(iv_b64))
    salt = base64.b64decode(_pad_b64(salt_b64))
    ct   = base64.b64decode(_pad_b64(ct_b64))

    kdf         = PBKDF2HMAC(algorithm=hashes.SHA256(), length=keylen_bits // 8,
                              salt=salt, iterations=iterations)
    derived_key = kdf.derive(key_bytes)
    aesgcm      = AESGCM(derived_key)
    aad         = json.dumps(adata, separators=(',', ':')).encode()
    plaintext   = aesgcm.decrypt(iv, ct, aad)

    if compression == 'zlib':
        plaintext = zlib.decompress(plaintext, -15)
    return plaintext.decode('utf-8')

def fetch_privatebin_paste(full_url):
    if '#' not in full_url:
        raise ValueError("URL has no key fragment (#...)")

    base_url, key_str = full_url.split('#', 1)
    headers = {'X-Requested-With': 'JSONHttpRequest', 'User-Agent': 'Mozilla/5.0'}

    resp = requests.get(base_url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if 'status' in data and data['status'] != 0:
        raise RuntimeError(f"Paste server error: {data.get('message', data['status'])}")

    if data.get('v', 1) == 2:
        return decrypt_privatebin_v2(data, key_str)

    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    spec     = data['data']
    iv_b64   = spec[0]
    salt_b64 = spec[1]
    its      = spec[2]
    klen     = spec[3]
    ct_b64   = data['data'][-1] if isinstance(data['data'], list) else data['ct']

    key_bytes   = base58_decode(key_str)
    iv          = base64.b64decode(_pad_b64(iv_b64))
    salt        = base64.b64decode(_pad_b64(salt_b64))
    ct          = base64.b64decode(_pad_b64(ct_b64))
    kdf         = PBKDF2HMAC(algorithm=hashes.SHA256(), length=klen // 8, salt=salt, iterations=its)
    derived_key = kdf.derive(key_bytes)
    aesgcm      = AESGCM(derived_key)
    aad         = json.dumps(data['adata'], separators=(',', ':')).encode() if 'adata' in data else b''
    plain       = aesgcm.decrypt(iv, ct, aad)
    return zlib.decompress(plain, -15).decode('utf-8')
