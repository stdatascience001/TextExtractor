# Dummy pytest module to satisfy imports in non-pytest environments

class MarkMock:
    def __getattr__(self, name):
        return lambda *args, **kwargs: lambda func: func

mark = MarkMock()

def fixture(*args, **kwargs):
    return lambda func: func
