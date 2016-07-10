import tempfile

from sqlalchemy.ext.declarative import declarative_base
from zope.sqlalchemy import ZopeTransactionExtension
import sqlalchemy.orm as orm
import sqlalchemy as sa

DB = orm.scoped_session(orm.sessionmaker(extension=ZopeTransactionExtension()))


class ORMClass(object):
    @classmethod
    def create(cls, **kws):
        instance = cls(**kws)
        DB.add(instance)
        return instance

    @classmethod
    def from_id(cls, id):
        return DB.query(cls).filter(cls.id == id).first()

    def delete(self):
        DB.delete(self)


Base = declarative_base(cls=ORMClass)


class Book(Base):
    __tablename__ = 'books'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.String)

    pages = sa.orm.relationship(
        'Page', order_by='Page.id', cascade='all, delete-orphan',
        back_populates='book')

    @classmethod
    def create(cls, title, f, extractor_cls, book_path):
        book = super(Book, cls).create(title=title)
        DB.flush()
        basedir = tempfile.mkdtemp(dir=book_path)
        extractor = extractor_cls(f, basedir)
        for page, mimetype in extractor.iter_pages():
            Page.create(book_id=book.id, path=page, mimetype=mimetype)
        return book


class Page(Base):
    __tablename__ = 'pages'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    path = sa.Column(sa.String, nullable=False, unique=True)
    mimetype = sa.Column(sa.String, nullable=False)

    book_id = sa.Column(sa.Integer, sa.ForeignKey('books.id'), nullable=False)

    book = sa.orm.relationship('Book', back_populates='pages', uselist=False)


def init_db(sqlalchemy_url):
    engine = sa.create_engine(sqlalchemy_url)
    DB.configure(bind=engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
