from __future__ import annotations

import os
from typing import List, Optional, Dict

import yaml
from yaml.scanner import ScannerError
from pydantic import BaseModel, ValidationError
from betterlogging import get_colorized_logger, DEBUG

CONFIG_STORAGE: Dict[str, Config] = {}

logger = get_colorized_logger('config_parser')
logger.setLevel(DEBUG)


class Config(BaseModel):
    group_mention: str
    question: str
    answer_wrong_button: str
    answer_right_button: str
    button_options: List[str]
    is_wrong_numbers_enabled: bool
    wrong_answers: Optional[List[str]] = []
    right_answer: str


for fp in os.listdir('../configs'):
    logger.info(f'Parsing {fp}...')

    with open(f'../configs/{fp}', encoding='utf-8') as f:
        if not (fp.endswith('.yml') or fp.endswith('.yaml')):
            logger.error(f'Configs directory contains unsupportable file - {fp}!')

        try:
            config = yaml.load(f, Loader=yaml.Loader)
        except ScannerError:
            logger.error(f'Failed to parse {fp}!')
            continue

        try:
            parsed_config = Config(**config)
        except ValidationError as e:
            logger.error(f'Illegal config format in {fp}! Details:')
            logger.exception(e)
            continue

        if parsed_config.right_answer not in parsed_config.button_options:
            logger.error('There is no right answer in button_options! Skipping...')

        parsed_config.group_mention = parsed_config.group_mention.lower()
        CONFIG_STORAGE[parsed_config.group_mention] = parsed_config
        logger.info('OK!')
