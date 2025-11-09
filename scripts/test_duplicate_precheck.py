import asyncio
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path('.').resolve()))

from api.app.repo.attribute_repo import AttributeRepo, DuplicateError
from api.app.models.dto import AttributeIn

class FakeResult:
    def __init__(self, rows):
        self._rows = rows
    def all(self):
        return self._rows

class FakeSession:
    def __init__(self, existing_rows):
        self.existing_rows = existing_rows
    async def execute(self, stmt):
        # Return a fake result where .all() returns the existing duplicates
        return FakeResult(self.existing_rows)

async def run_test():
    # Prepare a single row that would conflict with existing ('default','customer','cust_nm')
    ai = AttributeIn(entity='customer', logical_name='Customer Name', physical_name='cust_nm', data_type='text', category='entity')
    row = ai.model_dump() | {'version': 1, 'namespace': 'default'}

    # Fake session returns one existing tuple
    fake_existing = [('default', 'customer', 'cust_nm')]
    session = FakeSession(fake_existing)

    repo = AttributeRepo(session)

    try:
        await repo.bulk_insert([row])
    except DuplicateError as e:
        print('DuplicateError raised as expected:', e.duplicates)
        return 0
    except Exception as e:
        print('Unexpected exception:', type(e), e)
        return 2
    print('ERROR: bulk_insert did not raise DuplicateError')
    return 1

if __name__ == '__main__':
    exit(asyncio.run(run_test()))

