import pathlib
import textwrap
import enum
import re
import collections as c
from typing import List, Optional, OrderedDict, Tuple

class Types(enum.Enum):
    UINT16 = 2
    UINT64 = 8


class Languages(enum.Enum):
    Cxx = '.hpp'
    C = '.h'
    Python = '.py'


LANGUAGE_TYPES = {
    Languages.Cxx: {
        Types.UINT16: 'uint16_t',
        Types.UINT64: 'uint64_t',
    },
    Languages.C: {
        Types.UINT16: 'uint16_t',
        Types.UINT64: 'uint64_t',
    },
    Languages.Python: {
        Types.UINT16: 'np.uint16',
        Types.UINT64: 'np.uint64',
    }
}

# https://docs.python.org/3/library/struct.html#format-characters
PY_STRUCT_MAP = {
    Types.UINT16: 'H',
    Types.UINT64: 'Q'
}


class Message:
    def __init__(self, name: str, attributes: OrderedDict[str, Types]):
        self.name = name
        self.attributes = attributes

    def static_size(self) -> int:
        size = 0
        for attr_type in self.attributes.values():
            size += attr_type.value
        return size


class Parser:
    MESSAGE_RE = re.compile(r'^message (.*):$')
    ATTRIBUTE_RE = re.compile(f'^[\ |\t]*((?:{"|".join([_type.name.lower() for _type in Types])}))\ *(.*)$')
    COMMENT_RE = re.compile(r'^[\ |\t]*#.*$')

    @staticmethod
    def parse_file(file: pathlib.Path) -> List[Message]:
        messages = []
        data = file.read_text().split('\n')
        
        idx = 0
        while idx < len(data):
            name = Parser._match_top_level_message(data[idx])
            if name:
                idx = Parser._parse_message(data, idx + 1, name, messages)
            elif Parser._is_comment(data[idx]):
                pass
            elif len(data[idx]):
                raise ValueError(f'Failed to parse {data[idx]} as top-level '
                                  'message declaration')
            idx += 1
        
        return messages

    @staticmethod
    def _match_top_level_message(line: str) -> Optional[str]:
        match = Parser.MESSAGE_RE.match(line)
        if match is None:
            return None
        name = match.group(1)
        if name.isidentifier():
            return name
        return None

    @staticmethod
    def _parse_message(data: List[str], idx: int, name: str, messages: List[Message]) -> int:
        attributes: OrderedDict[str, Types] = c.OrderedDict()
        while idx < len(data):
            attribute = Parser._match_attribute(data[idx])
            if attribute:
                attributes[attribute[0]] = attribute[1]
            elif Parser._is_comment(data[idx]):
                pass
            elif len(data[idx]):
                raise ValueError(f'Failed to parse {data[idx]} as an attribute'
                                 f'of {name}')
            else:
                break
            idx += 1
        if len(attributes):
            messages.append(Message(name, attributes))
        else:
            raise ValueError(f'Expected {name} to have attributes')
        return idx - 1  # Back up so top-level parsing can increment

    @staticmethod
    def _match_attribute(line: str) -> Optional[Tuple[str, Types]]:
        match = Parser.ATTRIBUTE_RE.match(line)
        if match is None:
            return None
        name = match.group(2)
        _type = Types[match.group(1).upper()]
        return name, _type

    @staticmethod
    def _is_comment(line: str) -> bool:
        return Parser.COMMENT_RE.match(line) is not None


class Generator:
    TAB = '    '

    @staticmethod
    def generate(in_file: pathlib.Path, messages: List[Message]):
        for language in Languages:
            out_file = in_file.parent / (in_file.stem + '_bh' + language.value)

            if language == Languages.Cxx:
                Generator._generate_cxx(in_file, out_file, messages)
            elif language == Languages.C:
                Generator._generate_c(in_file, out_file, messages)
            elif language == Languages.Python:
                Generator._generate_python(in_file, out_file, messages)

    @staticmethod
    def _generate_python(in_file: pathlib.Path, out_file: pathlib.Path, messages: List[Message]):
        definitions = []
        type_map = LANGUAGE_TYPES[Languages.Python]
        for message in messages:
            attribute_definitions = ''
            for attr_name, attr_type in message.attributes.items():
                attribute_definitions += f'{Generator.TAB}{attr_name}: {type_map[attr_type]}\n'
            attribute_definitions = attribute_definitions

            constructor_definition = f'{Generator.TAB}def __init__(self, '
            constructor_implemenation = ''
            for attr_name, attr_type in message.attributes.items():
                constructor_definition += f'{attr_name}: {type_map[attr_type]}, '
                constructor_implemenation += f'{Generator.TAB * 2}self.{attr_name} = {attr_name}\n'
            constructor_definition = constructor_definition[:-2] + '):\n'
            constructor_implemenation = constructor_implemenation
            constructor = constructor_definition + constructor_implemenation

            buffer_size = (f'{Generator.TAB}def buffer_size(self) -> int:\n'
                           f'{Generator.TAB*2}return {message.static_size()}\n')

            struct_format_str = '>'
            struct_values = ''
            for attr_name, attr_type in message.attributes.items():
                struct_format_str += PY_STRUCT_MAP[attr_type]
                struct_values += f'self.{attr_name}, '
            struct_values = struct_values[:-2]
            encode = (f'{Generator.TAB}def encode(self) -> bytes:\n'
                      f'{Generator.TAB*2}return struct.pack(\'{struct_format_str}\', {struct_values})\n')

            struct_values = ''
            for attr_idx, attr in enumerate(message.attributes.items()):
                attr_name, attr_type = attr
                struct_values += f'{attr_name}={type_map[attr_type]}(e[{attr_idx}]), '
            struct_values = struct_values[:-2]
            decode = (f'{Generator.TAB}def decode(buffer: bytes) -> \'{message.name}\':\n'
                      f'{Generator.TAB*2}e = struct.unpack(\'{struct_format_str}\', buffer)\n'
                      f'{Generator.TAB*2}return {message.name}({struct_values})\n')

            definitions.append(
                f'class {message.name}:\n'
                f'{attribute_definitions}\n'
                f'{constructor}\n'
                f'{buffer_size}\n'
                f'{encode}\n'
                f'{decode}'
                f'\n'
                )

        header = textwrap.dedent(f"""\
            \"\"\"
            AUTOGENERATED CODE. DO NOT EDIT.
            Buffham generated from {in_file.name}
            \"\"\"
            import numpy as np
            import struct
        
        
            """)

        with open(out_file, 'w') as fp:
            fp.write(header)
            for definition in definitions:
                fp.write(definition)

    @staticmethod
    def _generate_cxx(in_file: pathlib.Path, out_file: pathlib.Path, messages: List[Message]):
        definitions = []
        type_map = LANGUAGE_TYPES[Languages.Cxx]
        for message in messages:
            attribute_definitions = ''
            for attr_name, attr_type in message.attributes.items():
                attribute_definitions += f'{Generator.TAB}{type_map[attr_type]} {attr_name};\n'
            attribute_definitions = attribute_definitions

            # constructor_definition = f'{Generator.TAB}{message.name}('
            # constructor_implemenation = ''
            # for attr_name, attr_type in message.attributes.items():
            #     constructor_definition += f'{type_map[attr_type]} {attr_name}, '
            #     constructor_implemenation += f'{Generator.TAB * 2}this->{attr_name} = {attr_name};\n'
            # constructor_definition = constructor_definition[:-2] + ')'
            # constructor_implemenation = constructor_implemenation
            # constructor = constructor_definition + ' {\n' + constructor_implemenation + f'{Generator.TAB}}}\n'

            buffer_size = (f'{Generator.TAB}size_t buffer_size() {{\n'
                           f'{Generator.TAB*2}return {message.static_size()};\n'
                           f'{Generator.TAB}}}\n')

            encode_memcpy = ''
            buf_idx = 0
            for attr_name, attr_type in message.attributes.items():
                encode_memcpy += f'{Generator.TAB*2}memcpy(buffer.get() + {buf_idx}, &{attr_name}, {attr_type.value});\n'
                buf_idx += attr_type.value
            encode = (f'{Generator.TAB}std::unique_ptr<uint8_t> encode() {{\n'
                      f'{Generator.TAB*2}std::unique_ptr<uint8_t> buffer(new uint8_t({message.static_size()}));\n'
                      f'{encode_memcpy}'
                      f'{Generator.TAB*2}return buffer;\n'
                      f'{Generator.TAB}}}\n')

            decode_initializer = '{ '
            buf_idx = 0
            for attr_name, attr_type in message.attributes.items():
                decode_initializer += f'*({type_map[attr_type]}*)(buffer.get() + {buf_idx}), '
                buf_idx += attr_type.value
            decode_initializer = decode_initializer[:-2] + ' }'
            decode = (f'{Generator.TAB}static {message.name} decode(const std::unique_ptr<uint8_t>& buffer, size_t len) {{\n'
                      f'{Generator.TAB*2}return {decode_initializer};\n'
                      f'{Generator.TAB}}}\n')

            definitions.append(
                f'struct {message.name} {{\n'
                f'{attribute_definitions}\n'
                # f'{constructor}\n'
                f'{buffer_size}\n'
                f'{encode}\n'
                f'{decode}'
                f'}};\n'
                )



        header = textwrap.dedent(f"""\
            /*
             * AUTOGENERATED CODE. DO NOT EDIT.
             * Buffham generated from {in_file.name}
             */
            #include <stdint.h>
            #include <string.h>
            #include <memory>
        
        
            """)

        with open(out_file, 'w') as fp:
            fp.write(header)
            for definition in definitions:
                fp.write(definition)

    @staticmethod
    def _generate_c(in_file: pathlib.Path, out_file: pathlib.Path, messages: List[Message]):
        definitions = []
        type_map = LANGUAGE_TYPES[Languages.Cxx]
        for message in messages:
            attribute_definitions = ''
            for attr_name, attr_type in message.attributes.items():
                attribute_definitions += f'{Generator.TAB}{type_map[attr_type]} {attr_name};\n'
            attribute_definitions = attribute_definitions

            # constructor_definition = f'{Generator.TAB}{message.name}('
            # constructor_implemenation = ''
            # for attr_name, attr_type in message.attributes.items():
            #     constructor_definition += f'{type_map[attr_type]} {attr_name}, '
            #     constructor_implemenation += f'{Generator.TAB * 2}this->{attr_name} = {attr_name};\n'
            # constructor_definition = constructor_definition[:-2] + ')'
            # constructor_implemenation = constructor_implemenation
            # constructor = constructor_definition + ' {\n' + constructor_implemenation + f'{Generator.TAB}}}\n'

            buffer_size = (f'size_t {message.name}_buffer_size({message.name}* inst) {{\n'
                           f'{Generator.TAB}return {message.static_size()};\n'
                           f'}}\n\n')

            encode_memcpy = ''
            buf_idx = 0
            for attr_name, attr_type in message.attributes.items():
                encode_memcpy += f'{Generator.TAB}memcpy(buffer + {buf_idx}, &inst->{attr_name}, {attr_type.value});\n'
                buf_idx += attr_type.value
            encode = (f'uint8_t* {message.name}_encode({message.name}* inst) {{\n'
                      f'{Generator.TAB}uint8_t* buffer = (uint8_t*)malloc({message.static_size()});\n'
                      f'{encode_memcpy}'
                      f'{Generator.TAB}return buffer;\n'
                      f'}}\n\n')

            decode_initializer = '{ '
            buf_idx = 0
            for attr_name, attr_type in message.attributes.items():
                decode_initializer += f'*({type_map[attr_type]}*)(buffer + {buf_idx}), '
                buf_idx += attr_type.value
            decode_initializer = decode_initializer[:-2] + ' }'
            decode = (f'{message.name} {message.name}_decode(uint8_t* buffer, size_t len) {{\n'
                      f'{Generator.TAB}RawImuData msg = {decode_initializer};\n'
                      f'{Generator.TAB}return msg;\n'
                      f'}}\n\n')

            definitions.append(
                f'typedef struct {{\n'
                f'{attribute_definitions}'
                f'}} {message.name};\n\n'
                # f'{constructor}\n'
                f'{buffer_size}'
                f'{encode}'
                f'{decode}'
                )



        header = textwrap.dedent(f"""\
            /*
             * AUTOGENERATED CODE. DO NOT EDIT.
             * Buffham generated from {in_file.name}
             */
            #include <stdint.h>
            #include <stdlib.h>
            #include <string.h>
        
        
            """)

        with open(out_file, 'w') as fp:
            fp.write(header)
            for definition in definitions:
                fp.write(definition)


if __name__ == '__main__':
    file = pathlib.Path('imu.bh')
    messages = Parser.parse_file(file)
    Generator.generate(file, messages)
