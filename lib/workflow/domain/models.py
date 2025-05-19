from typing import Optional, Tuple, Dict, List, Any, Union
from typing_extensions import Protocol
import attr
import os
import numpy as np

@attr.s(frozen=True)
class WorkflowProgress:
    percentage: int = attr.ib()
    message: str = attr.ib(default="")


@attr.s(frozen=True)
class WorkflowConfig:
    source_folder_path: str = attr.ib()
    ruler_position: str = attr.ib()
    photographer: str = attr.ib()
    obj_bg_mode: str = attr.ib()
    add_logo: bool = attr.ib(default=False)
    logo_path: Optional[str] = attr.ib(default=None)
    raw_ext: str = attr.ib(default=".cr2")
    valid_img_exts: List[str] = attr.ib(factory=lambda: [".jpg", ".jpeg", ".tiff", ".tif", ".png"])
    view_original_suffix_patterns: Dict[str, str] = attr.ib(factory=dict)
    temp_extracted_ruler_filename: str = attr.ib(default="temp_ruler_extracted.png")
    object_artifact_suffix: str = attr.ib(default="_artifact.png")
    museum_selection: str = attr.ib(default="British Museum")


@attr.s(frozen=True)
class RulerTemplates:
    ruler_template_1cm: str = attr.ib()
    ruler_template_2cm: str = attr.ib()
    ruler_template_5cm: str = attr.ib()


@attr.s(frozen=True)
class StepAllocation:
    scale: float = attr.ib(default=0.15)
    ruler_art: float = attr.ib(default=0.1)
    ruler_part_extract: float = attr.ib(default=0.05)
    digital_ruler_choice: float = attr.ib(default=0.05)
    digital_ruler_resize: float = attr.ib(default=0.1)
    other_obj: float = attr.ib(default=0.3)
    stitch: float = attr.ib(default=0.25)


class ProgressCallback(Protocol):
    def __call__(self, percentage: int) -> None:
        ...


class FinishedCallback(Protocol):
    def __call__(self) -> None:
        ...


@attr.s(frozen=True)
class WorkflowResult:
    total_ok: int = attr.ib(default=0)
    total_err: int = attr.ib(default=0)
    cr2_conv_total: int = attr.ib(default=0)
