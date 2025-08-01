from loguru import logger
logger.remove()
logger.add(lambda msg: print(msg, end=""), level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
