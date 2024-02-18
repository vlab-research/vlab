from typing import Annotated, Any, Union

from environs import Env
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from ..study_conf import (AudienceConf, CreativeConf, DataSourceConf,
                          DestinationConf, GeneralConf, InferenceDataConf,
                          RecruitmentConf, StratumConf, VariableConf)
from .auth import AuthError, verify_token
from .db import create_study_conf, get_all_study_confs, get_study_conf, copy_confs

app = FastAPI()


origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


env = Env()


class User(BaseModel):
    user_id: str


security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> User:
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = verify_token(token)
        user: str = payload.get("sub")

        if user is None:
            raise credentials_exception

        return User(user_id=user)

    except AuthError:
        raise credentials_exception


async def create_conf(user: User, org_id: str, slug: str, conf_type: str, config: Any):
    if isinstance(config, list):
        dat = [c.dict() for c in config]
    else:
        dat = config.dict()

    conf = create_study_conf(user.user_id, org_id, slug, conf_type, dat)
    return {"data": conf}


@app.post("/{org_id}/studies/{slug}/confs/general", status_code=201)
async def create_general_conf(
    org_id: str,
    slug: str,
    config: GeneralConf,
    user: Annotated[User, Depends(get_current_user)],
):
    return await create_conf(user, org_id, slug, "general", config)


@app.post("/{org_id}/studies/{slug}/confs/recruitment", status_code=201)
async def create_recruitment_conf(
    org_id: str,
    slug: str,
    config: RecruitmentConf,
    user: Annotated[User, Depends(get_current_user)],
):
    return await create_conf(user, org_id, slug, "recruitment", config)


@app.post("/{org_id}/studies/{slug}/confs/destinations", status_code=201)
async def create_destinations_conf(
    org_id: str,
    slug: str,
    config: list[DestinationConf],
    user: Annotated[User, Depends(get_current_user)],
):
    return await create_conf(user, org_id, slug, "destinations", config)


@app.post("/{org_id}/studies/{slug}/confs/creatives", status_code=201)
async def create_creative_conf(
    org_id: str,
    slug: str,
    config: list[CreativeConf],
    user: Annotated[User, Depends(get_current_user)],
):
    return await create_conf(user, org_id, slug, "creatives", config)


@app.post("/{org_id}/studies/{slug}/confs/audiences", status_code=201)
async def create_audience_conf(
    org_id: str,
    slug: str,
    config: list[AudienceConf],
    user: Annotated[User, Depends(get_current_user)],
):
    return await create_conf(user, org_id, slug, "audiences", config)


@app.post("/{org_id}/studies/{slug}/confs/variables", status_code=201)
async def create_variables_conf(
    org_id: str,
    slug: str,
    config: list[VariableConf],
    user: Annotated[User, Depends(get_current_user)],
):
    return await create_conf(user, org_id, slug, "variables", config)


@app.post("/{org_id}/studies/{slug}/confs/strata", status_code=201)
async def create_strata_conf(
    org_id: str,
    slug: str,
    config: list[StratumConf],
    user: Annotated[User, Depends(get_current_user)],
):
    return await create_conf(user, org_id, slug, "strata", config)


@app.post("/{org_id}/studies/{slug}/confs/data-sources", status_code=201)
async def create_data_sources_conf(
    org_id: str,
    slug: str,
    config: list[DataSourceConf],
    user: Annotated[User, Depends(get_current_user)],
):
    return await create_conf(user, org_id, slug, "data_sources", config)


@app.post("/{org_id}/studies/{slug}/confs/inference-data", status_code=201)
async def create_inference_data_conf(
    org_id: str,
    slug: str,
    config: InferenceDataConf,
    user: Annotated[User, Depends(get_current_user)],
):
    return await create_conf(user, org_id, slug, "inference_data", config)


class CopyFromConf(BaseModel):
    source_study_slug: str


@app.post("/{org_id}/studies/{slug}/copy-from", status_code=201)
async def copy_confs_from(
    org_id: str,
    slug: str,
    config: CopyFromConf,
    user: Annotated[User, Depends(get_current_user)],
):

    raw_config = copy_confs(user.user_id, org_id, slug, config.source_study_slug)
    return {"data": raw_config}


@app.get("/{org_id}/studies/{slug}/confs/{conf_type}")
async def get_conf(
    org_id: str,
    slug: str,
    conf_type: str,
    user: Annotated[User, Depends(get_current_user)],
):
    raw_config = get_study_conf(user.user_id, org_id, slug, conf_type)
    return {"data": raw_config}


@app.get("/{org_id}/studies/{slug}/confs")
async def get_all_confs(
    org_id: str,
    slug: str,
    user: Annotated[User, Depends(get_current_user)],
):
    raw_config = get_all_study_confs(user.user_id, org_id, slug)
    return {"data": raw_config}


@app.get("/health", status_code=200)
async def health():
    # TODO: add DB ping
    return "OK"
