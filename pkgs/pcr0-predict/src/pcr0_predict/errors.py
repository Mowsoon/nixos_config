class PredictError(Exception):
    pass


class EventLogError(PredictError):
    pass


class FirmwareError(PredictError):
    pass


class CalibrationError(PredictError):
    pass


class PcrlockError(PredictError):
    pass


class InputError(PredictError):
    pass
