import re
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from pcr12.errors import CredentialError
from pcr12.measure import Credential

POLICY_CREDENTIAL = re.compile(r"pcrlock\.[A-Za-z0-9_-]+\.cred")


class Decryptor(Protocol):
    def decrypt(self, credential: Credential) -> bytes: ...


def verify(
    credentials: Sequence[Credential],
    entry_credentials: Sequence[Path],
    policy: bytes,
    decryptor: Decryptor,
) -> None:
    if entry_credentials:
        listed = ", ".join(str(path) for path in entry_credentials)
        raise CredentialError(f"credentials found in boot entry drop-ins: {listed}")
    names = [credential.name for credential in credentials]
    if len(credentials) != 1 or not POLICY_CREDENTIAL.fullmatch(names[0]):
        listed = ", ".join(names) or "none"
        raise CredentialError(f"the ESP must hold only the pcrlock credential, found {listed}")
    if decryptor.decrypt(credentials[0]).rstrip(b"\n") != policy.rstrip(b"\n"):
        raise CredentialError(f"{names[0]} does not hold the current pcrlock policy")
