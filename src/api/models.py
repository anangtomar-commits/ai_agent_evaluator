from pydantic import RootModel


# {'filename.ext': ['chunk 1 text', 'chunk 2 text', ...]}
ExtractionResponse = RootModel[dict[str, list[str]]]
