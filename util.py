
from card_types import Monster

def get_concrete_subclasses(cls):
    subclasses = cls.__subclasses__()
    if not subclasses:
        return [cls]
    result = []
    for subclass in subclasses:
        result.extend(get_concrete_subclasses(subclass))
    return result



