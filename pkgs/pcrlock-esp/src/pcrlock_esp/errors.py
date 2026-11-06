class PcrlockEspError(Exception):
    pass


class InputError(PcrlockEspError):
    pass


class CommandError(PcrlockEspError):
    pass


class WriteError(PcrlockEspError):
    pass
