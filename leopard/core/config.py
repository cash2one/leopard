import os
import yaml

CONFIG_ROOT = os.path.join('leopard', 'conf')
CONFIG_FILE_EXTENSION = 'yaml'


def load_yaml_file(yaml_file):
    with open(yaml_file, encoding='utf-8') as file:
        rv = yaml.load(file.read())
    return rv


def get_config(config_id):
    config = load_yaml_file(os.path.join(CONFIG_ROOT,
                            os.extsep.join([config_id,
                                           CONFIG_FILE_EXTENSION])))
    return config
