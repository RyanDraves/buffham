# BuffHam
A simple, lightweight utility to encode and decode messages.

## Current Features
- Generates language-specific files from generic message definitions
- Supports a limited subset of statically-sized data types
- Languages supported:
  - C++

## Possible Roadmap
- Expand language support (Python)
- Add static data types
  - Other primitives not yet added
  - Fixed sized arrays
- Add dynamically sized data types
  - Strings
  - Arbitrary buffers
  - Dynamically sized arrays
  - Smart implementation of booleans (they share the same byte)
- Nested messages & message definitions
- Include messages from one file to another
- Custom encodings of method definitions
  - Differential encoding
  - Classical compression algorithms
- Add error detection and correction
