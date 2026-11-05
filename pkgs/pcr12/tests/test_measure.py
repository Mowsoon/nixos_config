import hashlib

from pcr12 import measure
from pcr12.measure import Credential

CREDENTIALS = [Credential("b.cred", b"second"), Credential("a.cred", b"first!")]


def _entries(archive: bytes) -> list[tuple[str, int, int, bytes]]:
    entries = []
    offset = 0
    while offset < len(archive):
        header = archive[offset : offset + 110]
        fields = [int(header[6 + 8 * index : 14 + 8 * index], 16) for index in range(13)]
        name_end = offset + 110 + fields[11]
        name = archive[offset + 110 : name_end - 1].decode("utf-8")
        data_start = name_end + (-name_end % 4)
        data = archive[data_start : data_start + fields[6]]
        entries.append((name, fields[0], fields[1], data))
        offset = data_start + fields[6] + (-fields[6] % 4)
    return entries


def test_archive_lists_directories_sorted_files_and_trailer() -> None:
    names = [entry[0] for entry in _entries(measure.archive(CREDENTIALS))]
    assert names == [
        "/.extra",
        "/.extra/global_credentials",
        ".extra/global_credentials/a.cred",
        ".extra/global_credentials/b.cred",
        "TRAILER!!!",
    ]


def test_archive_numbers_inodes_and_sets_modes() -> None:
    entries = _entries(measure.archive(CREDENTIALS))
    assert [(entry[1], entry[2]) for entry in entries] == [
        (1, 0o040555),
        (2, 0o040500),
        (3, 0o100400),
        (4, 0o100400),
        (5, 0o100000),
    ]


def test_archive_carries_the_credential_contents() -> None:
    assert _entries(measure.archive(CREDENTIALS))[2][3] == b"first!"


def test_archive_is_four_byte_aligned() -> None:
    assert len(measure.archive(CREDENTIALS)) % 4 == 0


def test_records_are_empty_without_credentials() -> None:
    assert measure.records([]) == []


def test_records_hash_the_archive() -> None:
    expected = hashlib.sha256(measure.archive(CREDENTIALS)).digest()
    assert measure.records(CREDENTIALS) == [expected]


def test_archive_digest_is_stable() -> None:
    digest = measure.records(CREDENTIALS)[0].hex()
    assert digest == "249ca3e7a3f72a46df29cc10b3230496080b0c0dedf23dca076f81b78e4ec230"


def test_replay_extends_from_zero() -> None:
    digest = bytes([1]) * 32
    assert measure.replay([digest]) == hashlib.sha256(bytes(32) + digest).digest()


def test_replay_of_nothing_is_the_empty_pcr() -> None:
    assert measure.replay([]) == bytes(32)
