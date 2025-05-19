from abc import ABC, abstractmethod
from metadata.domain import ImageMetadata

class MetadataProvider(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def apply_metadata(self, image_path: str, metadata: ImageMetadata) -> bool:
        pass
