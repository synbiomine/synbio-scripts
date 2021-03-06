#!/usr/bin/env python3

import glob
import jargparse
import os
import rdflib
from colorama import Fore, Back, Style
from rdflib.namespace import RDF
import sys

sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)) + '/../../../modules/python')
import intermyne.metadata as immd
import intermyne.model as imm
import intermyne.utils as imu
import synbio.data as sbd

#################
### FUNCITONS ###
#################
def getSoTermItemForSbolRole(o, soTermItems):
    soTerm = o.split('/')[-1]
    print('Got SOTerm [%s]' % soTerm)
    if soTerm not in soTermItems:
        soTermItems[soTerm] = addSoTermItem(doc, soTerm)
    return soTermItems[soTerm]


def getOrgItemForSynbisNativeFrom(o, orgItems):
    print('Got organism [%s]' % o)
    if o != '':
        if o not in organismItems:
            organismItems[o] = addOrganismItem(doc, o)
        return organismItems[o]
    else:
        return None


def addTopLevelItem(doc, name, componentUrl, graph, itemMap, dsItem=None):

    item = doc.createItem(name)
    if dsItem != None:
        item.addToAttribute('dataSets', dsItem)

    addPropertiesFromRdfItem(graph, componentUrl, itemMap, item)

    doc.addItem(item)
    return item


def addPropertiesFromRdfItem(graph, rdfItemUrl, itemMap, item):

    query = 'SELECT ?p ?o WHERE { <%s> ?p ?o . }' % rdfItemUrl
    # print(query)
    rows = graph.query(query)

    for p, o in rows:
        p = str(p)
        o = str(o)

        if p in itemMap:
            imAttrName = itemMap[p]

            if imAttrName == None:
                pass
            elif type(imAttrName) is list:
                key, value = imAttrName
                if key == None:
                    value(graph, o, item)
                else:
                    imAttrValue = value(o)
                    if imAttrValue != None:
                        item.addAttribute(key, imAttrValue)
            else:
                item.addAttribute(imAttrName, o)
        else:
            print(Fore.YELLOW + 'WARNING: Ignoring (%s, %s) as not found in item map' % (p, o) + Fore.RESET)


def addOrganismItem(doc, synbisName):
    SYNBIS_NATIVEFROM_NAMES_TO_TAXON_IDS = {
        'E. coli': 562
    }

    item = doc.createItem('Organism')
    if synbisName in SYNBIS_NATIVEFROM_NAMES_TO_TAXON_IDS:
        taxonId = SYNBIS_NATIVEFROM_NAMES_TO_TAXON_IDS[synbisName]
    else:
        taxonId = 0

    item.addAttribute('taxonId', taxonId)
    doc.addItem(item)

    return item


def addSoTermItem(doc, id):
    item = doc.createItem('SOTerm')
    item.addAttribute('identifier', id)
    doc.addItem(item)

    return item


def addRdfItems(type, graph, imItems, addFunc):
    rdfItems = graph.triples((None, RDF.type, rdflib.term.URIRef(type)))

    imu.printSection('Adding items for RDF nodes of type %s' % type)

    count = processed = 0
    for url, _, _ in rdfItems:
        count += 1
        url = str(url)
        if url not in imItems:
            print('Adding %s to imItems' % url)
            imItems[url] = addFunc(url, graph)
            processed += 1

    print('Added %d items out of %d' % (processed, count))

############
### MAIN ###
############
parser = jargparse.ArgParser('Take raw data downloaded from synbis and turn into InterMine Item XML.')
parser.add_argument('colPath', help='path to the data collection.')
parser.add_argument('-d', '--dummy', action='store_true', help='dummy run, do not store anything')
parser.add_argument('-v', '--verbose', action='store_true', help='be verbose')
args = parser.parse_args()

dc = sbd.Collection(args.colPath)
ds = dc.getSet('parts/synbis')
ds.startLogging(__file__)

model = dc.getModel()
doc = imm.Document(model)
dataSourceItem = immd.addDataSource(doc, 'SynBIS', 'http://synbis.bg.ic.ac.uk')
dataSetItem = immd.addDataSet(doc, 'SYNBIS parts', dataSourceItem)

sheetItems = {}
partItems = {}
sequenceItems = {}
organismItems = {}
soTermItems = {}

sequenceItemMap = {
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type':None,
    'http://sbols.org/v2#persistentIdentity':None,
    'http://sbols.org/v2#displayId':None,
    'http://sbols.org/v2#encoding':'encoding',
    'http://sbols.org/v2#elements':'residues'
}

partItemMap = {
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'   :None,
    'http://sbols.org/v2#displayId'                     :'name',
    'http://sbols.org/v2#persistentIdentity'            :'uri',
    'http://sbols.org/v2#role'                          :['role', lambda o: getSoTermItemForSbolRole(o, soTermItems)],
    'http://sbols.org/v2#sequence'                      :['sequence', lambda o: sequenceItems[o]],
    'http://sbols.org/v2#type'                          :'type',
    'http://synbis.bg.ic.ac.uk/nativeFrom'              :['organism', lambda o: getOrgItemForSynbisNativeFrom(o, organismItems)],
    'http://synbis.bg.ic.ac.uk/origin'                  :'origin',
    'http://synbis.bg.ic.ac.uk/rnapSpecies'             :'rnapSpecies',
    'http://synbis.bg.ic.ac.uk/rnapSigmaFactor'         :'rnapSigmaFactor',
    'http://synbis.bg.ic.ac.uk/inducer'                 :'inducer',
    'http://synbis.bg.ic.ac.uk/regulatoryElement'       :'regulatoryElement'
}

datasheetMap = {
    'http://sbols.org/v2#version':'version',
    'http://synbis.bg.ic.ac.uk/collectionLocation':'collectionLocation',
    'http://synbis.bg.ic.ac.uk/collector':'collector',
    'http://synbis.bg.ic.ac.uk/componentDefinition':[None, lambda g, rdfItemUrl, imItem : addPropertiesFromRdfItem(g, rdfItemUrl, partItemMap, imItem)],
    'http://synbis.bg.ic.ac.uk/curationLocation':'curationLocation',
    'http://synbis.bg.ic.ac.uk/curator':'curator'
}

for partsPath in glob.glob(ds.getRawPath() + 'parts/*.xml'):
    imu.printSection('Analyzing ' + partsPath)
    with open(partsPath) as f:
        g = rdflib.Graph()
        g.load(f)
        # print(g.serialize(format='turtle').decode('unicode_escape'))

        addRdfItems('http://sbols.org/v2#Sequence', g, sequenceItems, lambda url, graph: addTopLevelItem(doc, 'SynBioSequence', url, graph, sequenceItemMap))
        addRdfItems('http://synbis.bg.ic.ac.uk/Datasheet', g, sheetItems, lambda url, graph: addTopLevelItem(doc, 'SynBioPart', url, graph, datasheetMap, dsItem=dataSetItem))
        # addRdfItems('http://sbols.org/v2#ComponentDefinition', g, partItems, lambda url, graph: addTopLevelItem(doc, 'SynBioPart', url, graph, partItemMap, dsItem=dataSetItem))

if not args.dummy:
    doc.write(ds.getLoadPath() + 'items.xml')
