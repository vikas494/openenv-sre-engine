from pydantic import BaseModel, Field
from typing import Literal, Optional

# ---------------------------------------------------------
# 1. OBSERVATION: What the AI sees at every step
# ---------------------------------------------------------
class SREObservation(BaseModel):
    ticket_description: str = Field(
        description="The initial PagerDuty alert or incident description. Remains constant."
    )
    last_command_output: str = Field(
        description="The terminal output or file contents resulting from your last action. Read this carefully to decide your next move."
    )
    services_available: list[str] = Field(
        description="List of microservices you can investigate in this environment."
    )
    step_count: int = Field(
        description="The number of actions you have taken so far."
    )

# ---------------------------------------------------------
# 2. ACTION: What the AI is allowed to do
# ---------------------------------------------------------
class SREAction(BaseModel):
    command: Literal["query_logs", "inspect_config", "submit_resolution"] = Field(
        description="The action to perform. 'query_logs' reads service logs. 'inspect_config' reads config files. 'submit_resolution' ends the investigation with a fix."
    )
    target: str = Field(
        description="The target of the command. For logs: the service name (e.g., 'auth_service'). For config: the filename (e.g., 'db_config.json'). For resolution: a short summary of the root cause."
    )
    proposed_fix: Optional[str] = Field(
        default=None,
        description="The exact command or configuration change to fix the issue. ONLY required if command is 'submit_resolution'."
    )

# ---------------------------------------------------------
# 3. REWARD: How we grade the AI (Partial Progress)
# ---------------------------------------------------------
class SREReward(BaseModel):
    value: float = Field(
        description="The numerical reward for the current step (0.0 to 1.0)."
    )
    reason: str = Field(
        description="Explanation of why this reward was given (e.g., 'Correctly identified the failing service (+0.2)')."
    )