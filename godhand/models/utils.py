from uuid import uuid4

from couchdb.mapping import Document


class GodhandDocument(Document):
    MAX_STRING = u'\ufff0'

    @classmethod
    def generate_id(cls):
        return uuid4().hex
