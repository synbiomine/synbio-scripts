#!/usr/bin/python

from lxml import etree

class Model:
  def __init__(self, fn):
    self.modelTree = etree.parse(fn)

class Document:
  def __init__(self, model, outFn):
    self.model = model
    self.outFn = outFn