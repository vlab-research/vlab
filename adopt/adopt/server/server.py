import logging
from typing import Annotated, Any, Optional, Sequence
from datetime import datetime
from environs import Env
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
import pandas as pd

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
    report = updater.execute(Instruction(**(instruction.dict())))
    return OptimizeReport(**report)


@app.get("/{org_id}/optimize/{slug}")
async def optimize_study(
    org_id: str,
    slug: str,
    user: Annotated[User, Depends(get_current_user)],
) -> OptimizeResult:
    try:
        instructions = run_study_opt(user.user_id, org_id, slug)

    except BaseException as e:
        raise HTTPException(status_code=500, detail=f"{e}")

    # quick hack to deal with namedtuple.
    # Should replace w/ pydantic model
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
async def get_current_data(
    org_id: str,
    slug: str,
    user: Annotated[User, Depends(get_current_user)],
) -> CurrentDataResult:
    try:
        df = await fetch_current_data(user.user_id, org_id, slug)

        if df is None:
            return CurrentDataResult(data=[])

        # Convert DataFrame rows to CurrentDataRow objects
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


class RecruitmentStatsRow(BaseModel):
    """Statistics for a single stratum."""

    spend: float
    impressions: int
    reach: int
    cpm: float
    unique_clicks: int
    unique_ctr: float
    respondents: int
    price_per_respondent: float
    incentive_cost: float
    total_cost: float
    conversion_rate: float

    class Config:
        schema_extra = {
            "example": {
                "spend": 1000.0,
                "impressions": 50000,
                "reach": 25000,
                "cpm": 20.0,
                "unique_clicks": 1000,
                "unique_ctr": 0.02,
                "respondents": 100,
                "price_per_respondent": 10.0,
                "incentive_cost": 1000.0,
                "total_cost": 2000.0,
                "conversion_rate": 0.1,
            }
        }


class RecruitmentStatsResult(BaseModel):
    """Response containing recruitment statistics for all strata."""

    data: dict[str, RecruitmentStatsRow]

    class Config:
        schema_extra = {
            "example": {
                "data": {
                    "stratum1": {
                        "spend": 1000.0,
                        "impressions": 50000,
                        "reach": 25000,
                        "cpm": 20.0,
                        "unique_clicks": 1000,
                        "unique_ctr": 0.02,
                        "respondents": 100,
                        "price_per_respondent": 10.0,
                        "incentive_cost": 1000.0,
                        "total_cost": 2000.0,
                        "conversion_rate": 0.1,
                    }
                }
            }
        }


@app.get(
    "/{org_id}/studies/{slug}/recruitment-stats",
    response_model=RecruitmentStatsResult,
    responses={
        200: {"description": "Successfully retrieved recruitment statistics"},
        401: {"description": "Unauthorized - Invalid or missing authentication token"},
        404: {"description": "Study not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_recruitment_stats(
    org_id: str,
    slug: str,
    user: Annotated[User, Depends(get_current_user)],
) -> RecruitmentStatsResult:
    """
    Get recruitment statistics for each stratum in the study.

    This endpoint returns comprehensive statistics about recruitment performance
    for each stratum in the study, including spend, impressions, reach, and
    conversion metrics.

    Args:
        org_id: Organization ID
        slug: Study slug
        user: Authenticated user (injected by FastAPI)

    Returns:
        RecruitmentStatsResult containing statistics for each stratum

    Raises:
        HTTPException: If study not found or other errors occur
    """
    try:
        study_id = get_study_id(user.user_id, org_id, slug)
        if not study_id:
            raise HTTPException(status_code=404, detail=f"Study not found: {slug}")

        # Get study configuration
        study_confs = get_all_study_confs(user.user_id, org_id, slug)
        if not study_confs:
            raise HTTPException(
                status_code=404, detail=f"Study configuration not found: {slug}"
            )

        strata = [StratumConf(**s) for s in study_confs.get("strata", [])]

        print(study_confs)
        if not strata:
            raise HTTPException(
                status_code=404, detail=f"No strata found for study: {slug}"
            )

        # Get recruitment data
        from ..recruitment_data import get_recruitment_data

        rd = get_recruitment_data(db_cnf, study_id)

        # Get current data if available
        df = await fetch_current_data(user.user_id, org_id, slug)

        # Calculate stats using the full date range
        from ..budget import calculate_strata_stats
        from ..facebook.state import DateRange
        from datetime import datetime

        window = DateRange(datetime.min, datetime.max)
        stats = calculate_strata_stats(
            df=df,
            strata=strata,
            window=window,
            rd=rd,
            incentive_per_respondent=study_confs.get("recruitment", {}).get(
                "incentive_per_respondent", 0
            ),
        )

        return RecruitmentStatsResult(data=stats)

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting recruitment stats for study {slug}: {str(e)}")
        if "Could not find study id" in str(e):
            raise HTTPException(status_code=404, detail=f"Study not found: {slug}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get recruitment statistics: {str(e)}"
        )


@app.get("/health", status_code=200)
async def health():
    # TODO: add DB ping
    return "OK"
