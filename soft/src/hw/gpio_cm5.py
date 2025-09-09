import gpiod

class GPIO:
    def __init__(self, chip="/dev/gpiochip0"):
        self.chip = gpiod.Chip(chip)
        self.lines = {}

    def setup_out(self, pin, initial=0):
        line = self.chip.get_line(pin)
        config = gpiod.LineRequest()
        config.consumer = "cm5"
        config.request_type = gpiod.LINE_REQ_DIR_OUT
        line.request(config, default_vals=[initial])
        self.lines[pin] = line

    def setup_in(self, pin):
        line = self.chip.get_line(pin)
        config = gpiod.LineRequest()
        config.consumer = "cm5"
        config.request_type = gpiod.LINE_REQ_DIR_IN
        line.request(config)
        self.lines[pin] = line

    def write(self, pin, value):
        if pin not in self.lines:
            raise RuntimeError(f"Pin {pin} not configured as output")
        self.lines[pin].set_value(1 if value else 0)

    def read(self, pin):
        if pin not in self.lines:
            raise RuntimeError(f"Pin {pin} not configured as input")
        return self.lines[pin].get_value()
