import logging


class Loggable:
    """
    Make a class loggable.

    A Mixin that uses the __init_subclass__ hook to automatically inject
    a named logger into any subclass based on its module and class name.
    """

    logger: logging.Logger

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Automatically create a logger named 'module.ClassName'
        # This runs once when the class is defined (imported), not instantiated.
        logger_name = f"{cls.__module__}.{cls.__name__}"
        cls.logger = logging.getLogger(logger_name)
