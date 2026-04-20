# -*- coding: utf-8 -*-

import os
import sys

USER_HOME = os.environ.get('SCIKMS_USER_HOME', os.path.expanduser('~'))


if sys.platform == 'linux':
    CONFIG_DIR = os.environ.get(
        'XDG_CONFIG_HOME', os.path.join(USER_HOME, '.config'))
    DATA_DIR = os.environ.get(
        'XDG_DATA_HOME', os.path.join(USER_HOME, '.local', 'share'))
    STATE_DIR = os.environ.get(
        'XDG_STATE_HOME', os.path.join(USER_HOME, '.local', 'state'))
    CACHE_DIR = os.environ.get(
        'XDG_CACHE_HOME', os.path.join(USER_HOME, '.cache'))

    HOME_DIR = os.path.join(CONFIG_DIR, 'scikms')
    DATA_DIR = os.path.join(DATA_DIR, 'scikms')
    STATE_DIR = os.path.join(STATE_DIR, 'scikms')
    CACHE_DIR = os.path.join(CACHE_DIR, 'scikms')

    USER_PLUGINS_DIR = os.path.join(DATA_DIR, 'plugins')
    USER_THEMES_DIR = os.path.join(DATA_DIR, 'themes')

    LOG_FILE = os.path.join(STATE_DIR, 'stdout.log')
    STATE_FILE = os.path.join(STATE_DIR, 'state.json')
    DEFAULT_RCFILE_PATH = os.path.join(HOME_DIR, 'scikmsrc')
else:
    HOME_DIR = os.path.join(USER_HOME, '.scikms')
    DATA_DIR = os.path.join(HOME_DIR, 'data')
    STATE_DIR = DATA_DIR
    CACHE_DIR = os.path.join(HOME_DIR, 'cache')
    USER_PLUGINS_DIR = os.path.join(HOME_DIR, 'plugins')
    USER_THEMES_DIR = os.path.join(HOME_DIR, 'themes')

    LOG_FILE = os.path.join(HOME_DIR, 'stdout.log')
    STATE_FILE = os.path.join(DATA_DIR, 'state.json')
    DEFAULT_RCFILE_PATH = os.path.join(USER_HOME, '.scikmsrc')
