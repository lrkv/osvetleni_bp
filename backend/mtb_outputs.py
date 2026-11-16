"""Output encoders selected from the module type reported by MTB daemon."""


class UniOutputs:
    port_count = 16

    @staticmethod
    def encode(value):
        return {"type": "plain" if value in (0, 1) else "flicker", "value": value}

class UnisOutputs(UniOutputs):
    port_count = 28


class LedOutputs:
    port_count = 32

    @staticmethod
    def encode(value):
        if value not in (0, 1):
            raise ValueError("MTB-LED podporuje pouze zapnuto/vypnuto.")
        return bool(value)


FORMATS = {"MTB-UNI": UniOutputs, "MTB-UNI v2": UniOutputs,
           "MTB-UNI v4": UniOutputs, "MTB-UNIS": UnisOutputs, "MTB-LED": LedOutputs}


def output_format(module_type):
    if module_type not in FORMATS:
        raise ValueError(f"Nepodporovaný typ modulu {module_type!r}; výstupy nebyly odeslány.")
    return FORMATS[module_type]


def encode_outputs(module_type, outputs):
    encoder = output_format(module_type)
    for port, value in outputs.items():
        if type(port) is not int or not 0 <= port < encoder.port_count:
            raise ValueError(f"{module_type}: neplatný výstup {port}; povoleno 0–{encoder.port_count - 1}.")
        if type(value) is not int or value < 0:
            raise ValueError(f"Neplatná hodnota výstupu {port}: {value!r}.")
    return {port: encoder.encode(value) for port, value in outputs.items()}
