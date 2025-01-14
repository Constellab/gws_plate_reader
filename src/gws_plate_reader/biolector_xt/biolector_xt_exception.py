

class BiolectorXTConnectException(Exception):
    def __init__(self):
        super().__init__('Could not connect with the biolector device, is it on and available ?')
