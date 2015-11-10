import struct
import json
from typing import Optional, List


class DataBlock:

    def __init__(self, name):
        self.name = None
        self.data = None
        self.size = None
        self.encoding = None


def package(
        data: dict, data_blocks: Optional[List[DataBlock]]=[],
        header_fmt: str='>L',
        encoding: str='utf-8', errors: str='strict') -> bytes:
    """Packages a dict and optional data blocks according to the protocol

    Exceptions:
      ValueError:  disallowed key in input data dict
    """
    # Validate input data dict
    # Check for key 'data_blocks' (reserved for protocol use)
    if 'data_blocks' in data:
        raise ValueError('"data_blocks" key not allowed in input dict')

    # Convert input data dict to encoded byte string
    data_str = json.dumps(data, ensure_ascii=False)  # type: str
    data_bytes = data_str.encode(encoding=encoding)  # type: bytes

    # Get size of encoded JSON in number of bytes
    header_value = len(data_bytes)  # type: int

    # Package JSON size value into a 4 byte structure
    header_bytes = struct.pack(header_fmt, header_value)  # type: bytes

    data_block_bytes = b''  # type: bytes
    for data_block in data_blocks:
        pass

    return


def unpackage(
        data: bytes, header_fmt: str='>L',
        encoding: str='utf-8', errors: str='strict') -> dict:
    return
