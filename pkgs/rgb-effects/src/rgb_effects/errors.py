class RgbEffectsError(Exception):
    pass


class ConfigError(RgbEffectsError):
    pass


class KeyboardUnavailableError(RgbEffectsError):
    pass


class SessionError(RgbEffectsError):
    pass
