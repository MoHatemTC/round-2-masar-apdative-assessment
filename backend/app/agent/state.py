"""
State definition for the Adaptive Assessment Engine.
Uses Pydantic v2 to structure the session state and strip transient variables.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class AgentStateModel(BaseModel):
    # Core Orchestration Fields
    session_id: str = Field(
        default="",
        description="Unique identifier for the active assessment session."
    )
    question_number: int = Field(
        default=0,
        description="The sequence index of the question for enforcing uniqueness and resumability."
    )
    current_competency: Optional[str] = Field(
        default=None, 
        description="The competency currently being assessed (e.g., 'Python-Backend')."
    )
    sub_ids: List[str] = Field(
        default_factory=list, 
        description="List of question unique identifiers already served in this session."
    )
    turn_number: int = Field(
        default=0, 
        description="The current conversation/turn counter for this session."
    )
    
    # Adaptive Math History & Progress Tracking
    current_level_estimate: float = Field(
        default=3.0, 
        description="The running numerical estimate of the candidate's level (1.0 to 5.0)."
    )
    is_converged: bool = Field(
        default=False, 
        description="Flag tracking if the current competency assessment has reached a stopping condition."
    )
    completed_competencies: List[str] = Field(
        default_factory=list,
        description="List of competency names that have fully converged."
    )
    estimates: Dict[str, float] = Field(
        default_factory=dict,
        description="Mapping of competency names to their latest calculated level estimates."
    )

    # Allow dynamic extension and transient variables
    model_config = {
        "extra": "allow" # Allows storing dynamic variables or fields generated during execution
    }

    def to_persistent_dict(self) -> Dict[str, Any]:
        """
        Converts the Pydantic model to a raw dictionary and strictly strips out 
        all transient keys prefixed with an underscore '_'.
        """
        # Dump the model to a standard dictionary (Pydantic v2 uses model_dump)
        raw_dict = self.model_dump()
        
        # Filter out keys starting with '_'
        return {k: v for k, v in raw_dict.items() if not k.startswith("_")}