"""Implements the protocol for serializing and deserializing data using JSON


# Protocol defined as follows ##############################################

The connection shall be made with a TCP connection, thus ensuring properly
ordered receiving and data integrity.

The data will be packaged in three sections and is designed to allow
flexibility in modification from both the client and server end.  The first
two sections are required, while the third sections simple concatenates any
extra necessary data, and is parsed as defined in Section 2 (see below).


Section 1.  Size of JSON Header
    - This section is exactly 4 bytes in length
    - Indicates the size in bytes of Section 2 (needed to parse 2 from 3)
    - Defaults to little-endian unsigned long (i.e. '>L')
    - Includes size of all JSON, INCLUDING extra metadata added for extra
          data

Section 2.  JSON Data
    - Data dict serialized with JSON (UTF-8 encoded string by default)
    - Reserved keyword 'data_dict' (by default, can be changed):
        - Can contain any data, up to the server to interpret
    - Reserved keyword 'data_blocks' (by default, can be changed):
        - Value is a list of metadata for all additional data blocks
        - Each list entry contains at least the following keywords:
            - "name": Used to reference the extra data block
            - "size": Size in bytes of the data in Section 3
            - "encoding": String name of encoding if the data should be
                      interpreted as string (default 'utf-8')
                - All data is passes as byte strings, therefore encoding is
                      needed if the file should be interpreted as text.
                - Should be acceptable input to Python3.5 bytes.decode()
                      encoding parameter
        - The order of the 'data_blocks' metadata list must match the
              contiguous order of the concatenated binary data in Section 3

Section 3.  Extra Data Blocks
    - Limited to 4GB data blocks (due to max capacity constraints of size
          indicator in 'data_blocks')
    - Any extra data that is not parsed is ignored

############################################################################

Attributes:
    DATA_BLOCK_KEY (str): Key for serialized metadata of extra data blocks.
"""


import struct
import json
import logging


# Set up logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


# Constants (not intended to be changed, but could be in theory if needed)
HEADER_FORMAT = '>L'
# Metadata keywords
DATA_DICT_KEY = 'data_dict'
DATA_BLOCK_KEY = 'data_blocks'
# Serialization defaults
DFLT_ENCODING = 'utf-8'
DFLT_ERRORS = 'strict'


class DataBlock:

    """Container for managing data and metadata for serializing binary data

    Manages a byte string and associated metadata in a standardized
    container, thus simplifying management of this data in protocol
    serialization and deserialization functions.

    Instances of this class should be created for every block of binary
    data that will be passed over the network.
    """

    @classmethod
    def from_binary_io(cls, name, stream, encoding=None):
        """Instantiation method from a byte stream

        Args:
            name (str): Name for the DataBlock instance.
            stream (IO[bytes]): Binary stream source for the byte string
                data.
            encoding (Optional[str]): Encoding of the byte string if it is
                text. (default=None)

        Returns:
            DataBlock: New instance with no encoding by default.
        """
        return cls(name, stream.read(), encoding)

    @classmethod
    def from_binary_file(cls, name, stream):
        """Instantiation method from an open file object

        Note:
            Do NOT open file file with 'b' flag, as this method specifically
            assumes a unicode stream and an encoding property for the
            object.

        Args:
            name (str): Name for the DataBlock instance.
            stream (IO[str]): Binary stream source for the byte string data.

        Returns:
            DataBlock: New instance with the data as a byte string with
                encoding as detected by the file object encoding property.

        Raises:
            AttributeError: Given stream was not an open unicode file
                object.
        """
        return cls(
            name,
            stream.read().encode(stream.encoding),
            stream.encoding
        )

    def __init__(self, name, data, encoding=None):
        """Creates a new instance of DataBlock

        Sets attributes the the input parameters and size to the length of
        the given byte string.

        Args:
            name (str): Name for the DataBlock instance.
            data (bytes): Byte string of data to be sent.
            encoding (Optional[str]): Encoding of the byte string if it is
                text. (default=None)
        """
        self.name = name
        self.data = data
        self.encoding = encoding
        self.size = len(data)

    def metadata(self):
        """Prepares the metadata dict for this data block

        Creates and returns a dictionary of metadata for this datablock.
        Used to serialize the metadata for this datablock in the JSON
        section.

        Returns:
            Dict: Contains name, size, and encoding (if not None) metadata.
        """
        metadata_dict = {
            'name': self.name,
            'size': self.size,
        }
        # Only add encoding if an encoding was given
        if self.encoding:
            metadata_dict['encoding'] = self.encoding
        return metadata_dict


def serialize(
        data=None, data_blocks=None,
        encoding=DFLT_ENCODING, errors=DFLT_ERRORS):
    """Serializes a dict and optional DataBlocks according to the protocol

    Args:
        data (Dict): Data to be serialized and packaged into a byte string.
        data_blocks (List[DataBlock]): Zero or more DataBlock instances to
            be concatenated to the byte string. (default=[])
        encoding (str): Encoding for the JSON byte string. (default='utf-8')
        errors (str): Response when the JSON cannot be converted with the
            given encoding. (accepts: ['strict', 'replace', 'ignore'],
            default='strict')

    Returns:
        bytes: Byte string of a the dictionary serialized as JSON and all
               DataBlocks concatenated at the end.

    Exceptions:
      ValueError:  Disallowed key in input data dictionary.
    """
    # Set default values
    if data is None:
        data = {}
    if data_blocks is None:
        data_blocks = []

    serialize_data = {}

    # Validate error parameter
    if errors in ['strict', 'replace', 'ignore']:
        errors = errors
    else:
        errors = DFLT_ERRORS
    # Prepare the extra data blocks if any exist
    # If there are any data_blocks, add a list for the metadata
    if len(data_blocks) > 0:
        serialize_data[DATA_BLOCK_KEY] = []

    # Add the data block metadata to the data dict
    for data_block in data_blocks:
        serialize_data[DATA_BLOCK_KEY].append(data_block.metadata())
    # Concatenate all binary data
    data_block_bytes = b''.join(
        [block.data for block in data_blocks]
    )

    # Add the given data to the serialization dict
    if data:
        serialize_data[DATA_DICT_KEY] = data

    # Convert input data dict to encoded byte string
    data_str = json.dumps(serialize_data, ensure_ascii=False)
    data_bytes = data_str.encode(encoding=encoding, errors=errors)

    # Get size of encoded JSON in number of bytes
    header_value = len(data_bytes)
    # Package JSON size value into a 4 byte structure
    header_bytes = struct.pack(HEADER_FORMAT, header_value)

    return b''.join([header_bytes, data_bytes, data_block_bytes])


def deserialize(
        serialized_data,
        encoding=DFLT_ENCODING, errors=DFLT_ERRORS):
    """Deserializes a byte string to its original dict and DataBlocks

    Args:
        serialized_data (bytes): Byte string to be unpackaged according to
            the protocol
        encoding (str): Encoding for the JSON byte string. (default='utf-8')
        errors (str): Response when the JSON cannot be converted with the
            given encoding. (accepts: ['strict', 'replace', 'ignore'],
            default='strict')

    Returns:
        Tuple[Dict, List[DataBlock]]: Tuple with a dict of all original
            input data and a list of DataBlock objects if any exist.
    """
    # Validate error parameter
    if errors in ['strict', 'replace', 'ignore']:
        errors = errors
    else:
        errors = DFLT_ERRORS

    # Get header size from the first bytes of the data based on header format
    header_size = struct.calcsize(HEADER_FORMAT)
    header_bytes = serialized_data[:header_size]
    header_value = struct.unpack(HEADER_FORMAT, header_bytes)[0]

    data_bytes = serialized_data[
        header_size:header_size+header_value
    ]
    data_str = data_bytes.decode(encoding, errors=errors)
    data_dict = json.loads(data_str)

    blocks = []

    # Unpackage the original input dictionary
    unpacked_data = data_dict.get(DATA_DICT_KEY, {})

    # Unpackage any data blocks
    if DATA_BLOCK_KEY in data_dict:
        block_start = header_size+header_value
        for metadata in data_dict[DATA_BLOCK_KEY]:
            block = DataBlock(
                name=metadata['name'],
                data=serialized_data[block_start:block_start+metadata['size']],
                encoding=metadata['encoding'] \
                    if 'encoding' in metadata else None,
            )

            # Add to instance to list of all blocks
            blocks.append(block)

            # Adjust block starting point for next block
            block_start += metadata['size']

    return (unpacked_data, blocks)
