from pydm import Display
from qtpy.QtCore import QTimer
import logging
import random


logger = logging.getLogger('test.app')


class DemoDisplay(Display):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.next_message)
        self._timer.start(1000)
        self._words = ['study', 'the', 'past', 'if', 'you', 'would', 'define', 'future']

    def next_message(self):
        random.shuffle(self._words)
        message = ' '.join(self._words)
        rand_int = random.randint(0, 5)
        if rand_int == 0:
            logger.debug(message)
        elif rand_int == 1:
            logger.info(message)
        elif rand_int == 2:
            logger.warning(message)
        elif rand_int == 3:
            logger.error(message)
        elif rand_int == 4:
            logger.critical(message)
        else:
            logger.fatal(message)

    def ui_filename(self):
        return 'app.ui'
