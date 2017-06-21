# -*- coding: utf-8 -*-
"""
Created on Tue Jun 20 19:43:15 2017

@author: Jonah Hoffman
"""


class NonexistantFile(Exception):
    def __init__(self, file_name):
        self.args = ('No file "%s" found' % file_name,)


try:
    raise NonexistantFile('yo')
except Exception as inst:
    print(type(inst))    # the exception instance
    print(inst.args)     # arguments stored in .args
    print(inst)