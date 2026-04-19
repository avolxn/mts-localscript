from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from localscript.api.schemas import GenerateRequest, GenerateResponse
from localscript.core import Settings
from localscript.logs import configure_logging, get_logger
from localscript.modes import LuaCodegenMode, build_lua_codegen_mode

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if getattr(app.state, "codegen_mode", None) is None:
        settings = app.state.settings
        app.state.codegen_mode = build_lua_codegen_mode(settings)
    app.state.semaphore = asyncio.Semaphore(1)
    yield


def create_app(
    settings: Settings | None = None,
    *,
    codegen_mode: LuaCodegenMode | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    configure_logging(resolved_settings.runtime_dir)
    resolved_settings.validate_runtime()
    app = FastAPI(title="LocalScript API", version="2.0.0", lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.codegen_mode = codegen_mode

    @app.post("/generate", response_model=GenerateResponse)
    async def generate(request: GenerateRequest) -> GenerateResponse:
        try:
            async with app.state.semaphore:
                result = await app.state.codegen_mode.generate_one_shot_async(request.prompt)
        except ValueError as exc:
            logger.warning("Validation/model error during /generate: %s", exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover
            logger.exception("Unhandled exception during /generate.")
            raise HTTPException(status_code=502, detail=f"Ollama request failed: {exc}") from exc
        return GenerateResponse(code=result.final_code)

    return app
