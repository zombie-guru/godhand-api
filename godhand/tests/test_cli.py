from subprocess import check_call

from godhand.rest.tests.utils import ApiTest


class TestNoUsers(ApiTest):
    def test_update_user(self):
        from godhand.models.auth import User
        check_call([
            'godhand-cli',
            'update-user',
            '--couchdb-url', self.couchdb_url,
            'me@company.com',
            'user', 'admin',
        ], env=self.cli_env)
        User.from_email(self.authdb, 'user:')
