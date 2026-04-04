from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import traceback

from env import SREEnvironment
from models import SREAction

app = FastAPI(title="OpenEnv SRE Simulator")
sre_env = SREEnvironment()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "SRE Environment is running."}

@app.post("/reset")
def reset_env():
    try:
        obs = sre_env.reset()
        return {"observation": obs.model_dump(), "reward": 0.0, "done": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/state")
def get_state():
    try:
        obs = sre_env.state()
        return {"observation": obs.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/step")
def step_env(action: SREAction):
    try:
        obs, reward, done, info = sre_env.step(action)
        return {
            "observation": obs.model_dump(),
            "reward": reward.model_dump(),
            "done": done,
            "info": info
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))