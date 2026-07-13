from pathlib import Path

from neuralmarket.data.raw.integrity import sha256_of_file, verify_checksum


def test_sha256_of_file_matches_known_value(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.dbn"
    file_path.write_bytes(b"hello")
    digest = sha256_of_file(file_path)
    assert digest == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_verify_checksum_true_and_false(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.dbn"
    file_path.write_bytes(b"hello")
    digest = sha256_of_file(file_path)
    assert verify_checksum(file_path, digest) is True
    assert verify_checksum(file_path, "0" * 64) is False
