import logging
import sys
import time

import numpy as np
import requests

from bs4 import BeautifulSoup

def send_request(self, link, **kwargs):
    for i in range(3):
        try:
            self.logger.info('Attempt number %s of %s', i + 1, 3)
            r = requests.get(link, **kwargs, timeout=30)
            break
        except requests.exceptions.ConnectTimeout as err:
            self.logger.debug('Connection Timemout Error: %s', err)
            time.sleep(np.random.choice([x / 10 for x in range(7, 22)]))
            continue
        except requests.exceptions.RequestException as err:
            self.logger.debug('Connection Failed Error: %s', err)
            sys.exit()
    else:
        self.logger.debug('Number of attemps exceeded. Exiting script')
        sys.exit()
    return 


def set_logger(cls, filename):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(f"./logs/{filename}.log", mode="w", encoding='utf-8')
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


if __name__ == '__main__':
    start = time.perf_counter()
    finish = time.perf_counter()
    # app.logger.info('Finished in %s second(s)', {round(finish - start, 2)})
