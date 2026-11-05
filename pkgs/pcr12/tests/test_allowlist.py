from pathlib import Path

import pytest

from pcr12 import allowlist
from pcr12.errors import CredentialError
from pcr12.measure import Credential

POLICY = b"policy"
POLICY_CREDENTIAL = Credential("pcrlock.token.cred", POLICY)


class PlainDecryptor:
    def decrypt(self, credential: Credential) -> bytes:
        return credential.data


def test_verify_accepts_the_policy_credential_alone() -> None:
    allowlist.verify([POLICY_CREDENTIAL], [], POLICY, PlainDecryptor())


@pytest.mark.parametrize(
    "credentials",
    [
        [],
        [POLICY_CREDENTIAL, Credential("tmpfiles.extra.cred", b"x")],
        [Credential("nvpcr-anchor.token.cred", POLICY)],
        [Credential("pcrlock.token.cred.cred", POLICY)],
    ],
)
def test_verify_refuses_any_other_credential_set(credentials: list[Credential]) -> None:
    with pytest.raises(CredentialError):
        allowlist.verify(credentials, [], POLICY, PlainDecryptor())


def test_verify_accepts_a_policy_file_with_a_final_newline() -> None:
    allowlist.verify([POLICY_CREDENTIAL], [], POLICY + b"\n", PlainDecryptor())


def test_verify_refuses_a_policy_credential_with_other_content() -> None:
    with pytest.raises(CredentialError):
        allowlist.verify([POLICY_CREDENTIAL], [], b"older policy", PlainDecryptor())


def test_verify_refuses_credentials_of_a_boot_entry() -> None:
    entry = [Path("EFI/Linux/nixos.efi.extra.d/sysctl.extra.cred")]
    with pytest.raises(CredentialError):
        allowlist.verify([POLICY_CREDENTIAL], entry, POLICY, PlainDecryptor())
