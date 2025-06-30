"""
Support for dump, dumps, load, loads
"""
from pathlib import Path
from typing import TextIO

from pycodetags import DATA
from pycodetags.converters import convert_pep350_tag_to_DATA
from pycodetags.data_schema import PureDataSchema
from pycodetags.data_tags import DataTagSchema
from pycodetags.data_tags_parsers import iterate_comments


def dumps(obj:DATA)->str:
    if not obj:
        return ""
    # TODO: check plugins to answer for _schema
    return obj.as_data_comment()

def dump(obj:DATA, file:TextIO)->None:
    file.write(obj.as_data_comment())

def load(file:Path,encoding='ASCII', schema:DataTagSchema=PureDataSchema,include_folk_tags:bool=False)->list[DATA]:
    # pickle.load(file) files is a file like object, not path.
    return [convert_pep350_tag_to_DATA(_, schema) for _ in iterate_comments(
            file=str(file), schemas=[schema], include_folk_tags=include_folk_tags
    )]

def loads(data:str,schema:DataTagSchema=PureDataSchema,include_folk_tags:bool=False):
    # TODO: implement this.
    file = __file__
    return [convert_pep350_tag_to_DATA(_, schema) for _ in iterate_comments(
        file=str(file), schemas=[schema], include_folk_tags=include_folk_tags
    )]


