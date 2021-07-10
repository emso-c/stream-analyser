import logging

def create_logger(name, logpath, sid=None, format=None, level=logging.ERROR):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    if not format:
        if sid:
            format = f'%(asctime)s:%(module)s[%(lineno)d]:%(levelname)s:[{sid}]:%(message)s'
        else:
            format = f'%(asctime)s:%(module)s[%(lineno)d]:%(levelname)s:%(message)s'
    logging.basicConfig(
        level=level,
        format=format,
        filename=logpath,
        encoding='utf-8',
    )
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter(format))
    logging.getLogger(name).addHandler(console)
    return logging.getLogger(name)