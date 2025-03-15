import logging

# Create a logger for the instrumental_pipeline application
logger = logging.getLogger("instrumental_pipeline")
logger.setLevel(logging.INFO)  # Set to INFO or DEBUG as needed

# Create a stream handler (prints to console)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)

# Create a formatter and set it for the handler
formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] %(name)s: %(message)s")
stream_handler.setFormatter(formatter)

# Add the handler if not already present
if not logger.handlers:
    logger.addHandler(stream_handler)

# Optionally, disable propagation to avoid duplicate logging
logger.propagate = False

# Reduce SQLAlchemy engine logging verbosity if needed
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

logger.info("Logger is configured")
