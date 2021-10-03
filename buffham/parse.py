import pathlib
import textwrap
import enum
import re
from typing import Dict, List, Optional, Tuple

class Types(enum.Enum):
    UINT16 = 2
    UINT64 = 8


class Languages(enum.Enum):
    Cxx = '.hpp'


LANGUAGE_TYPES = {
    Languages.Cxx: {
        Types.UINT16: 'uint16_t',
        Types.UINT64: 'uint64_t'
    }
}


class Message:
    def __init__(self, name: str, attributes: Dict[str, Types]):
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
        attributes: Dict[str, Types] = {}
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
                encode_memcpy += f'{Generator.TAB*2}memcpy(buffer + {buf_idx}, &{attr_name}, {attr_type.value});\n'
                buf_idx += attr_type.value
            encode = (f'{Generator.TAB}uint8_t* encode() {{\n'
                      f'{Generator.TAB*2}uint8_t* buffer = new uint8_t({message.static_size()});\n'
                      f'{encode_memcpy}'
                      f'{Generator.TAB*2}return buffer;\n'
                      f'{Generator.TAB}}}\n')

            decode_initializer = '{ '
            buf_idx = 0
            for attr_name, attr_type in message.attributes.items():
                decode_initializer += f'*({type_map[attr_type]}*)(buffer + {buf_idx}), '
                buf_idx += attr_type.value
            decode_initializer = decode_initializer[:-2] + ' }'
            decode = (f'{Generator.TAB}static {message.name} decode(uint8_t* buffer, size_t len) {{\n'
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
            #include <cstring>
        
        
            """)

        with open(out_file, 'w') as fp:
            fp.write(header)
            for definition in definitions:
                fp.write(definition)


if __name__ == '__main__':
    file = pathlib.Path('imu.bh')
    messages = Parser.parse_file(file)
    Generator.generate(file, messages)
