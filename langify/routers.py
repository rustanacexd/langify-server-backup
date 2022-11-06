E2E_TEST = {'in_test_mode': False}


def in_test_mode():
    return E2E_TEST['in_test_mode']


def set_test_mode(test_mode):
    E2E_TEST['in_test_mode'] = test_mode


class E2ETestsRouter:
    e2e_test_database = 'e2e_tests'

    def db_for_read(self, model, **hints):
        if in_test_mode():
            return self.e2e_test_database

    def db_for_write(self, model, **hints):
        if in_test_mode():
            return self.e2e_test_database

    def allow_relation(self, obj1, obj2, **hints):
        if in_test_mode():
            return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True
