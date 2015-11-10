import struct
import json
from typing import Optional, List, IO


DATABLOCK_KEY = 'data_blocks'


class DataBlock:

    @classmethod
    def from_binary_io(
            cls, name: str, stream: IO[bytes],
            encoding: Optional[str]=None):
        """Instantiation method from a byte stream"""
        return cls(name, stream.read(), encoding)

    @classmethod
    def from_binary_file(
            cls, name: str, stream: IO[bytes],
            encoding: Optional[str]='utf-8'):
        """Copy of from_binary_io method with 'utf-8' encoding"""
        return cls.from_binary_io(name, stream, encoding)

    def __init__(self, name: str, data: bytes, encoding: Optional[str]=None):
        self.name = name  # type: str
        self.data = data  # type: bytes
        self.size = len(data)  # type: int
        self.encoding = encoding  # type: Optional[str]

    def metadata(self) -> dict:
        """Prepares the metadata dict for this data block"""
        metadata_dict = {
            'name': self.name,
            'size': self.size,
        }  # type: dict
        # Only add encoding if an encoding was given
        if self.encoding:
            metadata_dict['encoding'] = self.encoding  # type: str
        return metadata_dict



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
    if DATABLOCK_KEY in data:
        raise ValueError(
            '"{}" key not allowed in input dict'.format(DATABLOCK_KEY)
        )

    # Prepare the extra data blocks if any exist
    # If there are any data_blocks, add a list for the metadata
    if len(data_blocks) > 0:
        data[DATABLOCK_KEY] = []

    # Add the data block metadata to the data dict
    for data_block in data_blocks:
        data[DATABLOCK_KEY].append(data_block.metadata())
    # Concatenate all binary data
    data_block_bytes = b''.join(
        [block.data for block in data_blocks]
    )  # type: bytes

    # Convert input data dict to encoded byte string
    data_str = json.dumps(data, ensure_ascii=False)  # type: str
    data_bytes = data_str.encode(encoding=encoding)  # type: bytes

    # Get size of encoded JSON in number of bytes
    header_value = len(data_bytes)  # type: int
    # Package JSON size value into a 4 byte structure
    header_bytes = struct.pack(header_fmt, header_value)  # type: bytes

    return b''.join([header_bytes, data_bytes, data_block_bytes])


def unpackage(
        data: bytes, header_fmt: str='>L',
        encoding: str='utf-8', errors: str='strict') -> (dict, List[DataBlock]):
    # Get header size from the first bytes of the data based on header format
    header_size = struct.calcsize(header_fmt)  # type: int
    header_bytes = data[:header_size]  # type: bytes
    header_value = struct.unpack(header_fmt, header_bytes)[0]  # type: int

    data_bytes = data[header_size:header_size+header_value]  # type: bytes
    data_str = data_bytes.decode(encoding)  # type: str
    data_dict = json.loads(data_str)  # type: dict

    blocks = []
    if DATABLOCK_KEY in data_dict:
        block_start = header_size+header_value  # type: int
        for metadata in data_dict[DATABLOCK_KEY]:  # type: dict
            block = DataBlock(
                name=metadata['name'],
                data=data[block_start:block_start+metadata['size']],
                encoding=metadata['encoding'] if 'encoding' in metadata else None,
            )  # type: DataBlock

            # Add to instance to list of all blocks
            blocks.append(block)

            # Adjust block starting point for next block
            block_start += metadata['size']

        # Remote the block metadata as it was not in the original input dict
        del data_dict[DATABLOCK_KEY]

    return (data_dict, blocks)
