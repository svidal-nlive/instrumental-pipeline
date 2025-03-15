import os
import re
import hashlib

def to_snake_case(filename: str) -> str:
    """
    Converts a filename to snake_case.
    Splits the base name on " - " (with optional whitespace) and replaces
    internal spaces with underscores.
    
    Example:
      "01 - She Hates Me - Dierks Bentley.mp3" 
      -> "01_she_hates_me_dierks_bentley.mp3"
    """
    base_name, ext = os.path.splitext(filename)
    # Split the base name on hyphen with optional surrounding whitespace
    parts = re.split(r'\s*-\s*', base_name)
    # Trim each part, lower-case it, and replace internal spaces with underscores
    parts = [re.sub(r'\s+', '_', part.strip().lower()) for part in parts if part.strip()]
    new_base = "_".join(parts)
    # Collapse multiple underscores
    new_base = re.sub(r'_+', '_', new_base)
    return f"{new_base}{ext.lower()}"

def file_hash(file_data: bytes) -> str:
    """
    Returns the MD5 hash of the given file data.
    """
    md5 = hashlib.md5()
    md5.update(file_data)
    return md5.hexdigest()

def generate_task_id(filename: str, file_data: bytes) -> str:
    """
    Generates a unique task ID by combining a snake_case version of the filename
    with a short MD5 hash of the file data.
    """
    base_name, ext = os.path.splitext(to_snake_case(filename))
    hash_str = file_hash(file_data)[:8]
    return f"{base_name}_{hash_str}{ext}"
