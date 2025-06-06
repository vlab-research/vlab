import logging
from typing import Annotated, Any, Optional, Sequence, Dict
from datetime import datetime
from environs import Env
from fastapi import Depends, FastAPI, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
import pandas as pd
import asyncio
from functools import wraps
import time

from ..responses import get_inference_data

from ..campaign_queries import get_user_info
from ..facebook.update import GraphUpdater
from ..malaria import (
    Instruction,
    load_basics,
    run_instructions,
    update_ads_for_campaign,
)
from ..study_conf import (
    AudienceConf,
    CreativeConf,
    DataSourceConf,
    DestinationConf,
    GeneralConf,
    InferenceDataConf,
    RecruitmentConf,
    StratumConf,
    VariableConf,
)
from .auth import AuthError, generate_api_token, verify_tokens
from .db import (
    copy_confs,
    create_study_conf,
    db_cnf,
    get_all_study_confs,
    get_study_conf,
    get_study_id,
    insert_credential,
    query,
)
from ..recruitment_data import (
    AdPlatformRecruitmentStats,
    RecruitmentStats,
    RecruitmentStatsResponse,
)

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


class OptimizeInstruction(BaseModel):
    node: str
    action: str
    params: dict[str, Any]
    id: Optional[str] = None


class OptimizeReport(BaseModel):
    timestamp: str
    instruction: OptimizeInstruction


class InstructionResult(BaseModel):
    data: OptimizeReport


class OptimizeResult(BaseModel):
    data: Sequence[OptimizeInstruction]


class User(BaseModel):
    user_id: str


security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> User:
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = verify_tokens(token)
        user: str = payload.get("sub")

        if user is None:
            raise credentials_exception

        return User(user_id=user)

    except AuthError:
        raise credentials_exception


async def create_conf(user: User, org_id: str, slug: str, conf_type: str, config: Any):
    if isinstance(config, list):
        dat = [c.model_dump() for c in config]
    else:
        dat = config.model_dump()

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


def run_study_opt(user_id: str, org_id: str, slug: str) -> Sequence[Instruction]:
    logging.info(f"Optimizing Study: {slug}")
    study_id = get_study_id(user_id, org_id, slug)
    study, state = load_basics(study_id, db_cnf, env)
    instructions, _ = update_ads_for_campaign(db_cnf, study, state)
    return instructions


def run_single_instruction(
    user_id: str, org_id: str, slug: str, instruction: OptimizeInstruction
) -> OptimizeReport:
    # Replace with a more direct way of getting info, make endpoint
    # more flexible...
    # or just make another endpoint???

    # ad account
    # campaign_names
    # user = get_user_info(study_id, db_cnf)
    # state = FacebookState(
    #     get_api(env, user["token"]), study.general.ad_account, study.campaign_names
    # )

    study_id = get_study_id(user_id, org_id, slug)
    study, state = load_basics(study_id, db_cnf, env)

    updater = GraphUpdater(state)

    # hack to cast OptimizeInstruction to Instruction
    report = updater.execute(Instruction(**(instruction.model_dump())))
    return OptimizeReport(**report)


def async_timeout(seconds: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail=f"Operation timed out after {seconds} seconds",
                )

        return wrapper

    return decorator


@app.get("/{org_id}/optimize/{slug}")
@async_timeout(300)  # 5 minute timeout
async def optimize_study(
    org_id: str,
    slug: str,
    user: Annotated[User, Depends(get_current_user)],
) -> OptimizeResult:
    try:
        instructions = await asyncio.to_thread(
            run_study_opt, user.user_id, org_id, slug
        )
    except BaseException as e:
        logging.error(f"Error in optimize_study: {str(e)}")
        raise HTTPException(status_code=500, detail=f"{e}")

    res = OptimizeResult(
        data=[OptimizeInstruction(**i._asdict()) for i in instructions]
    )
    return res


class CurrentDataRow(BaseModel):
    user_id: str
    variable: str
    value: str | float | int
    timestamp: datetime


class CurrentDataResult(BaseModel):
    data: Sequence[CurrentDataRow]


async def fetch_current_data(
    user_id: str, org_id: str, slug: str
) -> pd.DataFrame | None:
    """Fetch current data from database for a given study"""
    study_id = get_study_id(user_id, org_id, slug)
    study, state = load_basics(study_id, db_cnf, env)

    inf_start, inf_end = study.recruitment.get_inference_window(datetime.now())
    return get_inference_data(
        study.user.survey_user, study.id, db_cnf, inf_start, inf_end
    )


@app.get("/{org_id}/optimize/{slug}/current-data")
@async_timeout(300)  # 5 minute timeout
async def get_current_data(
    org_id: str,
    slug: str,
    user: Annotated[User, Depends(get_current_user)],
) -> CurrentDataResult:
    try:
        df = await fetch_current_data(user.user_id, org_id, slug)

        if df is None:
            return CurrentDataResult(data=[])

        current_data = [
            CurrentDataRow(
                user_id=row.user_id,
                variable=row.variable,
                value=row.value,
                timestamp=row.timestamp,
            )
            for row in df.itertuples(index=False)
        ]

        return CurrentDataResult(data=current_data)
    except BaseException as e:
        logging.error(f"Error in get_current_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"{e}")


@app.post("/{org_id}/optimize/{slug}/instruction", status_code=201)
async def run_instruction(
    org_id: str,
    slug: str,
    instruction: OptimizeInstruction,
    user: Annotated[User, Depends(get_current_user)],
) -> InstructionResult:
    try:
        report = run_single_instruction(user.user_id, org_id, slug, instruction)
        return InstructionResult(data=report)
    except BaseException as e:
        raise HTTPException(status_code=500, detail=f"{e}")


class CreateApiKeyRequest(BaseModel):
    name: str


class CreateApiKeyResponseData(BaseModel):
    name: str
    id: str
    token: str


class CreateApiKeyResponse(BaseModel):
    data: CreateApiKeyResponseData


@app.post("/users/api-key", status_code=201)
async def create_api_key(
    key_request: CreateApiKeyRequest,
    user: Annotated[User, Depends(get_current_user)],
) -> CreateApiKeyResponse:
    try:
        token, token_id = generate_api_token(
            user_id=user.user_id, name=key_request.name
        )
        data = CreateApiKeyResponseData(name=key_request.name, token=token, id=token_id)
        return CreateApiKeyResponse(data=data)

    except BaseException as e:
        raise HTTPException(status_code=500, detail=f"{e}")


class RecruitmentStatsResult(BaseModel):
    """Response model for recruitment statistics endpoint."""

    data: Dict[str, RecruitmentStats]

    class Config:
        from_attributes = True


def get_latest_adopt_report(study_id: str) -> dict[str, int]:
    """Get the latest adopt report for a study and extract current participants.

    Args:
        study_id: The ID of the study

    Returns:
        A dictionary mapping stratum IDs to number of respondents
    """
    q = """
    SELECT details
    FROM adopt_reports
    WHERE study_id = %s
    AND report_type = 'FACEBOOK_ADOPT'
    ORDER BY created DESC
    LIMIT 1
    """

    res = query(db_cnf, q, (study_id,), as_dict=True)
    try:
        report = list(res)[0]["details"]
        # Extract current_participants from each stratum, only including those that have the data
        return {
            stratum_id: int(data["current_participants"])
            for stratum_id, data in report.items()
            if "current_participants" in data
        }
    except IndexError:
        raise HTTPException(
            status_code=404, detail=f"No adopt report found for study {study_id}"
        )
    except KeyError:
        raise HTTPException(
            status_code=500, detail=f"Invalid adopt report format for study {study_id}"
        )


@app.get(
    "/{org_id}/studies/{slug}/recruitment-stats",
    response_model=RecruitmentStatsResponse,
    responses={
        200: {"description": "Successfully retrieved recruitment statistics"},
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        404: {"description": "Study not found"},
        500: {"description": "Internal server error"},
        504: {"description": "Gateway timeout"},
    },
)
@async_timeout(300)  # 5 minute timeout
async def get_recruitment_stats(
    org_id: str,
    slug: str,
    user: Annotated[User, Depends(get_current_user)],
) -> RecruitmentStatsResponse:
    """
    Get recruitment statistics for a study.

    Args:
        org_id: Organization ID
        slug: Study slug
        user: Current user

    Returns:
        Recruitment statistics for each stratum
    """
    try:
        study_id = get_study_id(user.user_id, org_id, slug)
        if not study_id:
            raise HTTPException(status_code=404, detail=f"Study not found: {slug}")

        # Get study configuration
        study_confs = await asyncio.to_thread(
            get_all_study_confs, user.user_id, org_id, slug
        )
        if not study_confs:
            raise HTTPException(
                status_code=404, detail=f"Study configuration not found: {slug}"
            )

        strata = [StratumConf(**s) for s in study_confs.get("strata", [])]

        if not strata:
            raise HTTPException(
                status_code=404, detail=f"No strata found for study: {slug}"
            )

        # Get current data from adopt reports instead of fetch_current_data
        respondents_dict = await asyncio.to_thread(get_latest_adopt_report, study_id)

        # Calculate stats using the full date range
        from ..budget import calculate_strata_stats
        from ..facebook.state import DateRange
        from ..recruitment_data import calculate_stat_sql

        # TODO: make window a parameter
        window = None

        recruitment_stats = await asyncio.to_thread(
            calculate_stat_sql, db_cnf, window, study_id
        )

        stats = calculate_strata_stats(
            respondents_dict=respondents_dict,  # Pass the respondents dict
            strata=strata,
            recruitment_stats=recruitment_stats,
            incentive_per_respondent=study_confs.get("recruitment", {}).get(
                "incentive_per_respondent", 0
            ),
        )

        # Stats is already a Dict[str, RecruitmentStats], just wrap it in the response
        return RecruitmentStatsResponse(data=stats)

    except HTTPException:
        raise


@app.get("/health", status_code=200)
async def health():
    # TODO: add DB ping
    return "OK"
