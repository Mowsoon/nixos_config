class Pcr12Error(Exception):
    pass


class InputError(Pcr12Error):
    pass


class EventLogError(Pcr12Error):
    pass


class ModelError(Pcr12Error):
    pass


class CredentialError(Pcr12Error):
    pass


class EnrollError(Pcr12Error):
    pass
