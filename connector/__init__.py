import logging
import requests


class Connector:

    post_url = ''
    headers = {'x-teamtactics-token': 'None'}

    def __init__(self, config):
        print('Initializing connector')
        if config.has_option('connect', 'postUrl'):
            self.post_url = str(config['connect']['postUrl'])

        if self.post_url == '':
            print('No Url configured, only logging events')
        elif self.post_url != '':
            print('Using Url ' + self.post_url + ' to publish events')
            #            if config.has_option('connect', 'clientAccessToken'):
            self.headers = {'Content-Type': 'application/json'}

        if config.has_option('global', 'logfile'):
            logging.basicConfig(filename=str(config['global']['logfile']),
                                level=logging.INFO,
                                format='%(asctime)s$%(message)s')

    def publish(self, json_data):
        try:
            json_data = json_data.replace('\\u00fc', 'ü')\
                .replace('\\u00f6', 'ö')\
                .replace('\\u00e4', 'ä')\
                .replace('\\00df', 'ß')\
                .replace('\\u00dc', 'Ü')\
                .replace('\\u00d6', 'Ö')\
                .replace('\\u00ed', 'í')\
                .replace('\\u00c4', 'Ä').encode('utf-8')

            logging.info(json_data)
            if self.post_url != '':
                response = requests.post(self.post_url, data=json_data,
                                         headers=self.headers, timeout=10.0)
                return response

        except Exception as ex:
            print('Unable to publish data: ' + str(ex))
