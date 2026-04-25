"""Client-side user proof verification."""

import base64
import hashlib

class InvalidSignatureError(Exception):
    pass

def verify_ed25519_proof(pubkey_b64: str, signature_b64: str, message: str) -> None:
    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.exceptions import InvalidSignature
    except ImportError:
        raise RuntimeError("cryptography package is required for Ed25519 verification")
        
    try:
        pubkey_bytes = base64.b64decode(pubkey_b64)
        sig_bytes = base64.b64decode(signature_b64)
    except Exception as e:
        raise InvalidSignatureError("malformed base64") from e
        
    if len(pubkey_bytes) != 32:
        raise InvalidSignatureError("invalid pubkey length")
        
    if len(sig_bytes) != 64:
        raise InvalidSignatureError("invalid signature length")

    payload = f"{pubkey_b64}|{message}".encode("utf-8")
    
    try:
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pubkey_bytes)
        public_key.verify(sig_bytes, payload)
    except Exception as e:
        raise InvalidSignatureError("invalid signature") from e
        
def compute_proof_commit(pubkey_b64: str, message: str) -> str:
    payload = f"{pubkey_b64}|{message}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
