""" Tools to import metadata from open APIs.
"""
from SPARQLWrapper import SPARQLWrapper, JSON
import colander as co

from .utils import only_integers


class NoResultsForUri(ValueError):
    pass


class MangaSchema(co.MappingSchema):
    @co.instantiate()
    class name(co.SequenceSchema):
        value = co.SchemaNode(co.String())

    @co.instantiate()
    class description(co.SequenceSchema):
        value = co.SchemaNode(co.String())

    @co.instantiate()
    class author(co.SequenceSchema):
        value = co.SchemaNode(co.String())

    @co.instantiate()
    class magazine(co.SequenceSchema):
        value = co.SchemaNode(co.String())

    @co.instantiate()
    class genre(co.SequenceSchema):
        value = co.SchemaNode(co.String())

    @co.instantiate(preparer=only_integers)
    class number_of_volumes(co.SequenceSchema):
        value = co.SchemaNode(co.String())


def load_manga_resource(uri):
    client = SPARQLWrapper("http://dbpedia.org/sparql")
    client.setQuery('''
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT DISTINCT
    group_concat(distinct ?label, '|') as ?name
    group_concat(distinct ?author, '|') as ?author
    group_concat(distinct ?magazine, '|') as ?magazine
    group_concat(distinct ?genre, '|') as ?genre
    group_concat(distinct ?numberOfVolumes, '|') as ?number_of_volumes
    group_concat(distinct ?comment, '|') as ?description

    {

    ?book
      rdfs:label ?label ;
      dbo:numberOfVolumes ?numberOfVolumes ;
      rdfs:comment ?comment ;

      dbo:author _:author ;
      dbo:magazine _:magazine ;
      dbp:genre _:genre ;

      rdf:type dbo:Manga .

    _:author rdfs:label ?author .
    _:magazine rdfs:label ?magazine .
    _:genre rdfs:label ?genre .

    FILTER (lang(?author) = 'en')
    FILTER (lang(?magazine) = 'en')
    FILTER (lang(?comment) = 'en')
    FILTER (lang(?label) = 'en')
    FILTER (lang(?genre) = 'en')

    VALUES ?book { <%(uri)s> }

    } group by ?book LIMIT 1
    ''' % {'uri': uri})
    client.setReturnFormat(JSON)
    try:
        response = client.query().convert()['results']['bindings'][0]
    except IndexError:
        raise NoResultsForUri(uri)
    cstruct = {k: v['value'].split('|') for k, v in response.items()}
    return MangaSchema().deserialize(cstruct)
