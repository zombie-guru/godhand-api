from subprocess import check_call
import os

from godhand.rest.tests.utils import ApiTest

BUILDOUT_BIN_DIRECTORY = os.environ['BUILDOUT_BIN_DIRECTORY']


class TestNoUsers(ApiTest):
    def test_update_user(self):
        from godhand.models.auth import User
        check_call([
            os.path.join(BUILDOUT_BIN_DIRECTORY, 'godhand-cli'),
            'update-user',
            '--couchdb-url', self.couchdb_url,
            'me@company.com',
            'user', 'admin',
        ], env=self.cli_env)
        User.from_email(self.authdb, 'user:')
