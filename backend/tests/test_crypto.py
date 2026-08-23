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


def test_wrap_unwrap_bound_to_user() -> None:
    kek = Kek(new_dek())
    dek = new_dek()
    wrapped = kek.wrap(dek, "user-a")
    assert kek.unwrap(wrapped, "user-a") == dek
    with pytest.raises(CryptoError):
        kek.unwrap(wrapped, "user-b")


def test_nonces_are_unique() -> None:
    key = new_dek()
    assert encrypt(key, b"same", "a") != encrypt(key, b"same", "a")


def test_dek_cache_expiry() -> None:
    cache = DekCache(ttl=-1)
    cache.put("u", b"k")
    assert cache.get("u") is None
