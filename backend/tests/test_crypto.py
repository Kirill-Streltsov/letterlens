import pytest

from letterlens.crypto import CryptoError, DekCache, Kek, decrypt, encrypt, new_dek


def test_round_trip_and_aad_binding() -> None:
    key = new_dek()
    blob = encrypt(key, b"secret letter", "letter-1")
    assert decrypt(key, blob, "letter-1") == b"secret letter"
    with pytest.raises(CryptoError):
        decrypt(key, blob, "letter-2")  # ciphertext moved to another record


def test_tamper_detection() -> None:
    key = new_dek()
    blob = bytearray(encrypt(key, b"x" * 32, "a"))
    blob[-1] ^= 1
    with pytest.raises(CryptoError):
        decrypt(key, bytes(blob), "a")


