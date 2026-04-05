import os
import json
import traceback
from openai import OpenAI
from pydantic import ValidationError

# Import our custom environment and models
from server.env import SREEnvironment
from server.models import SREAction

def log_start(task: str, env_name: str, model: str):
    print(f"[START] task={task} env={env_name} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: str = None):
    # Booleans must be lowercase 'true'/'false'
    done_val = str(done).lower()
    # Error must be 'null' if None
    error_val = error if error else "null"

    # Action string should ideally be compact (no newlines)
    action_compact = action.replace("\n", " ").strip()
    
    print(f"[STEP] step={step} action={action_compact} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: list):
    # success must be lowercase
    success_val = str(success).lower()
    # rewards must be a comma-separated list WITHOUT brackets
    rewards_str = ",".join([f"{r:.2f}" for r in rewards])
    
    print(f"[END] success={success_val} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)

# ---------------------------------------------------------
# MAIN INFERENCE LOOP
# ---------------------------------------------------------
def main():
    # 1. Load credentials as mandated by the rules
    api_base_url = os.getenv("API_BASE_URL","https://openrouter.ai/api/v1")
    api_key = os.getenv("HF_TOKEN")
    model_name = os.getenv("MODEL_NAME", "qwen/qwen3.6-plus:free") # Fallback for local testing

    if not api_key:
        print("ERROR: HF_TOKEN environment variable not set.")
        return

    # Initialize OpenAI Client
    client = OpenAI(base_url=api_base_url, api_key=api_key)

    # Initialize our OpenEnv Simulator
    env = SREEnvironment()
    
    # Tracking variables
    rewards = []
    steps_taken = 0
    score = 0.0
    success = False
    
    # 2. Emit the required [START] log
    log_start(task=env.task_id, env_name="sre-incident-simulator", model=model_name)

    try:
        # Start the episode
        observation = env.reset()
        done = False
        
        # System prompt instructing the LLM exactly how to act and format its JSON
        messages = [
            {
                "role": "system", 
                "content": (
                    "You are an elite Site Reliability Engineer responding to a critical outage. "
                    "You must output your action as a raw JSON object and nothing else. Do NOT wrap it in markdown backticks.\n\n"
                    "Your JSON MUST strictly match this exact schema:\n"
                    "{\n"
                    '  "command": "query_logs" | "inspect_config" | "submit_resolution",\n'
                    '  "target": "name_of_service_or_file_to_check",\n'
                    '  "proposed_fix": "description of the fix (ONLY include this if command is submit_resolution)"\n'
                    "}"
                )
            }
        ]

        while not done:
            steps_taken += 1
            error_msg = None
            action_log_str = ""
            reward_val = 0.0

            # Add the current observation to the LLM's context
            obs_json = observation.model_dump_json()
            messages.append({"role": "user", "content": f"Current Status: {obs_json}"})

            try:
                # Use standard completion (works perfectly with OpenRouter and all open-source models)
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.1,
                )
                
                # Get the raw text from the AI
                raw_text = response.choices[0].message.content.strip()
                
                # Strip out the annoying Markdown backticks if the AI added them
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:-3].strip()
                elif raw_text.startswith("```"):
                    raw_text = raw_text[3:-3].strip()
                
                # Manually validate the clean text using our Pydantic model
                agent_action = SREAction.model_validate_json(raw_text)
                action_log_str = agent_action.model_dump_json()

                # Add the agent's action back to the message history
                messages.append({"role": "assistant", "content": action_log_str})

                # Step the environment!
                observation, reward, done, _ = env.step(agent_action)
                
                reward_val = reward.value
                rewards.append(reward_val)
                
                # If we hit max score on the final step, mark as success
                if done and reward_val == 1.0:
                    success = True

            except ValidationError as ve:
                error_msg = f"LLM output schema error: {ve}"
                done = True
            except Exception as e:
                error_msg = f"API or Execution Error: {str(e)}"
                done = True

            # 5. Emit the required [STEP] log
            log_step(
                step=steps_taken, 
                action=action_log_str if action_log_str else "ERROR", 
                reward=reward_val, 
                done=done, 
                error=error_msg
            )

        # Calculate final score (clamp between 0.0 and 1.0)
        # Summing rewards could exceed 1.0 depending on design, so we strictly clamp it.
        total_score = min(max(sum(rewards), 0.0), 1.0)
        
        # Override score to exactly 1.0 if successfully solved
        if success:
            total_score = 1.0

    except Exception as e:
        traceback.print_exc()
        success = False
        total_score = 0.0
    finally:
        # 6. Emit the required [END] log
        log_end(success=success, steps=steps_taken, score=total_score, rewards=rewards)

if __name__ == "__main__":
    main()