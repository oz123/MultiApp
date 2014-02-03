import logging, sys

class Logger(object):
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Logger, cls).__new__(cls, *args, **kwargs)
            cls._instance.logger = logging.getLogger('backoffice')
            cls._instance.logger.setLevel(logging.INFO)
            
            stdo_hdlr = logging.StreamHandler(sys.stdout)
            stdo_hdlr.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            stdo_hdlr.setFormatter(formatter)
            
            cls._instance.logger.addHandler(stdo_hdlr)
        
        return cls._instance

    @classmethod
    def info(cls, msg):
        cls._instance.logger.info(msg)
        
    @classmethod
    def warning(cls, msg):
        cls._instance.logger.warning(msg)

    @classmethod
    def error(cls, msg):
        cls._instance.logger.error(msg)


