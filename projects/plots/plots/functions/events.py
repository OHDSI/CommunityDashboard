from typing import Generic, TypeVar, Union

T = TypeVar('T')

class DatabaseTrigger(Generic[T]):
    oldValue: Union[T, None]
    updateMask: Union[dict, None]
    value: T

    def __init__(self, oldValue, updateMask, value) -> None:
        super().__init__()
        self.oldValue = oldValue
        self.updateMask = updateMask
        self.value = value