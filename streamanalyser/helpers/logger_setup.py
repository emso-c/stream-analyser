import logging

def create_logger(name, logpath, sid=None, format=None, def_level=logging.ERROR, level=logging.DEBUG):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    if not format:
        if sid:
            format = f'%(asctime)s:%(module)s[%(lineno)d]:%(levelname)s:[{sid}]:%(message)s'
        else:
            format = f'%(asctime)s:%(module)s[%(lineno)d]:%(levelname)s:%(message)s'
    logging.basicConfig(
        level=def_level,
        format=format,
        filename=logpath,
        encoding='utf-8',
    )
    console = logging.StreamHandler()
    console.setLevel(def_level)
    console.setFormatter(logging.Formatter(format))
    logging.getLogger(name).addHandler(console)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger