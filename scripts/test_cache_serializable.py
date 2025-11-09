import json
from api.app.repo import db
from api.app.models.dto import AttributeIn, AttributeOut
from api.app.repo.attribute_repo import _normalize_row

# Create a sample Pydantic input
ai = AttributeIn(entity='loan', logical_name='Loan Principal Balance', physical_name='ln_prin_bal', data_type='decimal', category='entity')
row = ai.model_dump() | {'version': 1}
row['namespace'] = 'default'

# Simulate SQLAlchemy object creation and Pydantic output model
obj = db.Attribute(**_normalize_row(row))
# Simulate DB-assigned id (flush/commit would normally provide this)
obj.id = 1
out = AttributeOut(**obj.__dict__)

# Ensure model_dump is JSON serializable
print(json.dumps(out.model_dump(mode="json")))
