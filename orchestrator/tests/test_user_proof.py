import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from orchestrator.cognition.user_proof import (
    InvalidSignatureError,
    compute_proof_commit,
    verify_ed25519_proof,
)


def test_ed25519_user_proof_round_trip_and_commit() -> None:
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pubkey_b64 = base64.b64encode(public_bytes).decode("ascii")
    message = "hello xion"
    signature = private_key.sign(f"{pubkey_b64}|{message}".encode())
    signature_b64 = base64.b64encode(signature).decode("ascii")

    verify_ed25519_proof(pubkey_b64, signature_b64, message)

    assert len(compute_proof_commit(pubkey_b64, message)) == 64
    assert compute_proof_commit(pubkey_b64, message) != compute_proof_commit(pubkey_b64, "different")


def test_ed25519_user_proof_rejects_wrong_message() -> None:
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pubkey_b64 = base64.b64encode(public_bytes).decode("ascii")
    signature = private_key.sign(f"{pubkey_b64}|hello xion".encode())

    with pytest.raises(InvalidSignatureError):
        verify_ed25519_proof(pubkey_b64, base64.b64encode(signature).decode("ascii"), "tampered")
