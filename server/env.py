import os
from typing import Tuple
from .models import SREObservation, SREAction, SREReward

class SREEnvironment:
    def __init__(self):
        # We MUST read which task to run from the environment variables. 
        # The OpenEnv validation runner will inject this automatically based on your YAML file.
        self.task_id = os.getenv("OPENENV_TASK_ID", "task_1_easy")
        
        self.step_count = 0
        self.max_steps = 10
        self.visited_clues = set() # To track partial progress
        
        # ---------------------------------------------------------
        # TASK DEFINITIONS (The "Mock" Virtual System)
        # ---------------------------------------------------------
        self.tasks = {
            "task_1_easy": {
                "ticket": "CRITICAL: Auth service is throwing 500 Internal Server Errors on all login attempts.",
                "logs": {
                    "auth_service": "ERROR [auth.py:42] KeyError: 'JWT_SECRET' not found in environment. Startup aborted.",
                    "payment_service": "INFO: Payment service running normally."
                },
                "configs": {},
                "target_clue_log": "auth_service",
                "solution_keywords": ["jwt", "secret", "environment", "env"]
            },
            "task_2_medium": {
                "ticket": "WARNING: Checkout API is timing out. Users cannot complete purchases.",
                "logs": {
                    "payment_service": "TimeoutError: Database connection pool exhausted. 0 connections available.",
                    "auth_service": "INFO: Auth running smoothly."
                },
                "configs": {
                    "db_config.json": '{"host": "db.internal", "port": 5432, "pool_size": 2, "timeout_ms": 5000}'
                },
                "target_clue_log": "payment_service",
                "target_clue_config": "db_config.json",
                "solution_keywords": ["pool", "size", "increase", "db_config"]
            },
            "task_3_hard": {
                "ticket": "PAGERDUTY: Cascading failure. API Gateway is returning 502 Bad Gateway for Inventory routes.",
                "logs": {
                    "api_gateway": "ERROR: 502 Bad Gateway - SSL Handshake Failed with downstream 'inventory_service'.",
                    "inventory_service": "WARN [tls.go:112]: Certificate expired on 2023-10-01. Rejecting incoming connections.",
                    "auth_service": "INFO: Auth OK."
                },
                "configs": {
                    "gateway_routing.yaml": "routes:\n  - path: /inventory\n    backend: https://inventory_service:8443"
                },
                "target_clue_log": "inventory_service",
                "solution_keywords": ["ssl", "certificate", "expired", "renew", "tls"]
            }
        }

    # ---------------------------------------------------------
    # CORE OPENENV METHODS
    # ---------------------------------------------------------
    def reset(self) -> SREObservation:
        """Starts a new episode based on the injected environment variable."""
        self.step_count = 0
        self.visited_clues = set()
        
        task_data = self.tasks[self.task_id]
        services = list(task_data["logs"].keys())
        
        return SREObservation(
            ticket_description=task_data["ticket"],
            last_command_output="System initialized. Waiting for commands...",
            services_available=services,
            step_count=self.step_count
        )

    def state(self) -> SREObservation:
        """Returns the current state (required by OpenEnv spec)."""
        task_data = self.tasks[self.task_id]
        return SREObservation(
            ticket_description=task_data["ticket"],
            last_command_output="Current State Request",
            services_available=list(task_data["logs"].keys()),
            step_count=self.step_count
        )

    def step(self, action: SREAction) -> Tuple[SREObservation, SREReward, bool, dict]:
        """Processes the AI's action and runs the Grader logic."""
        self.step_count += 1
        task_data = self.tasks[self.task_id]
        
        output = ""
        reward_value = 0.0
        reason = "Command executed with no significant progress."
        done = False

        # ACTION 1: Query Logs
        if action.command == "query_logs":
            if action.target in task_data["logs"]:
                output = task_data["logs"][action.target]
                # Partial Reward: Reduced to 0.1 to leave room for the final score
                if action.target == task_data.get("target_clue_log") and "log_found" not in self.visited_clues:
                    reward_value = 0.10 
                    reason = f"Good investigation! Found the critical error in {action.target} logs."
                    self.visited_clues.add("log_found")
            else:
                output = f"ERROR: Service '{action.target}' not found."
                reward_value = -0.01  # Slight penalty
                reason = "Queried a non-existent service."

        # ACTION 2: Inspect Config
        elif action.command == "inspect_config":
            if action.target in task_data.get("configs", {}):
                output = task_data["configs"][action.target]
                # Partial Reward: Reduced to 0.1 to leave room for the final score
                if action.target == task_data.get("target_clue_config") and "config_found" not in self.visited_clues:
                    reward_value = 0.10
                    reason = f"Great debugging! Found the misconfiguration in {action.target}."
                    self.visited_clues.add("config_found")
            else:
                output = f"ERROR: File '{action.target}' not found or permission denied."
                reward_value = -0.01

        # ACTION 3: Submit Resolution (THE GRADER)
        elif action.command == "submit_resolution":
            done = True
            fix_text = (action.proposed_fix or "").lower()
            
            # Check if the AI's proposed fix contains the required concepts
            matches = sum(1 for keyword in task_data["solution_keywords"] if keyword in fix_text)
            
            if matches >= 2: # Success threshold
                # Maximum score is 0.99. If they got 0.2 from partials, give them 0.79 here. 
                # If they skipped partials and just guessed the fix, give them 0.99 here.
                current_partials = len(self.visited_clues) * 0.10
                reward_value = 0.99 - current_partials 
                reason = "SUCCESS: Root cause correctly identified and valid fix proposed."
                output = "Incident resolved. System returning to normal."
            else:
                # Minimum score is 0.01 instead of 0.0
                reward_value = 0.01 
                reason = "FAILURE: Proposed fix does not address the root cause."
                output = "Fix deployed, but the system is still failing."
                
        # Enforce Episode Boundaries (Timeout)
        if self.step_count >= self.max_steps and not done:
            done = True
            reason = "FAILURE: Maximum steps reached. The SLA was breached and the system crashed."
            output = "Timeout."

        # Construct the response objects matching our Pydantic schemas
        observation = SREObservation(
            ticket_description=task_data["ticket"],
            last_command_output=output,
            services_available=list(task_data["logs"].keys()),
            step_count=self.step_count
        )
        
        reward = SREReward(value=reward_value, reason=reason)

        return observation, reward, done, {}
