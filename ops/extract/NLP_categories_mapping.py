from dataclasses import dataclass, field
from typing import List 

@dataclass 
class StandardCategory: 
    name: str 
    subcategories: List[str] = field(default_factory=list)
    subcategories: List[str] = field(default_factory=list) 
    
STANDDARD_CATEGORIES = {
    "Pastries": StandardCategory(
        name="Pastries",
        subcategories=["Croissants", "Pie", "Tart", "Danish", "Pain au"],
        keywords=[""]
    )
}