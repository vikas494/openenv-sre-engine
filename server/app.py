import uvicorn
from fastapi import FastAPI
from .env import SREEnvironment
from .models import SREAction

app = FastAPI()

# Initialize the environment globally so the API can talk to it
sre_env = SREEnvironment()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "SRE Environment is running."}

@app.post("/reset")
def reset_environment():
    """Resets the environment and returns the initial observation."""
    obs = sre_env.reset()
    return obs.model_dump()

@app.post("/step")
def step_environment(action: SREAction):
    """Takes a step in the environment."""
    obs, reward, done, info = sre_env.step(action)
    
    # Ensure reward is extracted correctly depending on your SREReward model
    reward_val = reward.value if hasattr(reward, 'value') else float(reward)
    
    return {
        "observation": obs.model_dump(),
        "reward": reward_val,
        "done": done,
        "info": info
    }

@app.get("/state")
def get_state():
    """Returns the current state of the environment."""
    return {
        "task_id": sre_env.task_id,
        "active": True
    }

def main():
    # Start the FastAPI server using uvicorn. 
    # Port 7860 is the standard default for Hugging Face Spaces.
    uvicorn.run(app, host="0.0.0.0", port=7860)

# This execution block MUST remain at the very end of the file
if __name__ == "__main__":
    main()