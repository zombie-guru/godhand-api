""" Tools to import metadata from open APIs.
"""
import logging

from SPARQLWrapper import SPARQLWrapper, JSON
import colander as co

from .utils import only_integers

LOG = logging.getLogger('opendata')


class NoResultsForUri(ValueError):
    pass


class MangaSchema(co.MappingSchema):
    @co.instantiate()
    class uri(co.SequenceSchema):
        value = co.SchemaNode(co.String())

    @co.instantiate()
    class name(co.SequenceSchema):
        value = co.SchemaNode(co.String())

    @co.instantiate()
    class description(co.SequenceSchema):
        value = co.SchemaNode(co.String())

    @co.instantiate(missing=None)
    class author(co.SequenceSchema):
        value = co.SchemaNode(co.String())

    @co.instantiate(missing=None)
    class magazine(co.SequenceSchema):
        value = co.SchemaNode(co.String())

    @co.instantiate(missing=None)
    class genre(co.SequenceSchema):
        value = co.SchemaNode(co.String())

    @co.instantiate(preparer=only_integers, missing=None)
    class number_of_volumes(co.SequenceSchema):
        value = co.SchemaNode(co.String())


def iterate_manga():
    client = SPARQLWrapper('http://dbpedia.org/sparql')
    offset = 0
    limit = 100
    while True:
        documents = get_manga(client, offset, limit)
        n_document = -1
        for n_document, document in enumerate(documents):
            yield document
        LOG.info('received batch ({}-{}): {} items'.format(
            offset, offset+limit, n_document + 1))
        if n_document < (limit - 1):
            return
        offset += limit


def get_manga(client, offset, limit):
    client.setQuery('''
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT DISTINCT
    ?book as ?uri
    group_concat(distinct ?label, '|') as ?name
    group_concat(distinct ?author, '|') as ?author
    group_concat(distinct ?magazine, '|') as ?magazine
    group_concat(distinct ?genre, '|') as ?genre
    group_concat(distinct ?numberOfVolumes, '|') as ?number_of_volumes
    group_concat(distinct ?comment, '|') as ?description

    {

    ?book
      rdfs:label ?label ;
      rdfs:comment ?comment ;
      rdf:type dbo:Manga .

    OPTIONAL {
        ?book dbo:numberOfVolumes ?numberOfVolumes .
    }
    OPTIONAL {
        ?book dbo:magazine _:magazine .
        _:magazine rdfs:label ?magazine .
        FILTER (lang(?magazine) = 'en')
    }
    OPTIONAL {
        ?book dbo:author _:author .
        _:author rdfs:label ?author .
        FILTER (lang(?author) = 'en')
    }
    OPTIONAL {
        ?book dbp:genre _:genre .
        _:genre rdfs:label ?genre .
        FILTER (lang(?genre) = 'en')
    }

    FILTER (lang(?label) = 'en')
    FILTER (lang(?comment) = 'en')
    } group by ?book OFFSET %(offset)d LIMIT %(limit)d
    ''' % {'offset': offset, 'limit': limit})
    client.setReturnFormat(JSON)
    response = client.query().convert()
    for document in response['results']['bindings']:
        cstruct = {
            k: v['value'].split('|') for k, v in document.items()
            if v['value'] != ''}
        yield MangaSchema().deserialize(cstruct)
