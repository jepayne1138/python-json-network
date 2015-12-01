#Python JSON Network
This is a package intended to simplify network communication for simple Python applications.  It wraps lower-level networking code in a basic endpoint class that is utilized as both the network client and server, and implements a custom protocol that serializes the data that is to be transfered as JSON and de-serializes upon receiving the byte-stream.

NOTE:  **Written with 3.5 type hints, no current plans to back-port to 2.7**

#JSON Serialization Protocol Definition
The connection shall be made with a TCP connection, thus ensuring properly
ordered receiving and data integrity.

The data will be packaged in three sections and is designed to allow
flexibility in modification from both the client and server end.  The first
two sections are required, while the third sections simple concatenates any
extra necessary data, and is parsed as defined in Section 2 (see below).


####Section 1.  Size of JSON Header
* This section is exactly 4 bytes in length
* Indicates the size in bytes of Section 2 (needed to parse 2 from 3)
* Defaults to little-endian unsigned long (i.e. '>L')
* Includes size of all JSON, INCLUDING extra metadata added for extra
      data

####Section 2.  JSON Data
* Data dict serialized with JSON (UTF-8 encoded string by default)
* Reserved keyword 'data_dict' (by default, can be changed):
    * Can contain any data, up to the server to interpret
* Reserved keyword 'data_blocks' (by default, can be changed):
    * Value is a list of metadata for all additional data blocks
    * Each list entry contains at least the following keywords:
        * "name": Used to reference the extra data block
        * "size": Size in bytes of the data in Section 3
        * "encoding": String name of encoding if the data should be
                  interpreted as string (default 'utf-8')
            * All data is passes as byte strings, therefore encoding is
                  needed if the file should be interpreted as text.
            * Should be acceptable input to Python3.5 bytes.decode()
                  encoding parameter
    * The order of the 'data_blocks' metadata list must match the
          contiguous order of the concatenated binary data in Section 3

####Section 3.  Extra Data Blocks
* Limited to 4GB data blocks (due to max capacity constraints of size
      indicator in 'data_blocks')
* Any extra data that is not parsed is ignored

**More details on the way...**
