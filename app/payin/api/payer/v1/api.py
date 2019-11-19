from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.status import HTTP_200_OK, HTTP_201_CREATED
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.payin.api.payer.v1.request import CreatePayerRequest, UpdatePayerRequestV1
from app.payin.core.exceptions import PayinError, PayinErrorCode
from app.payin.core.payer.model import Payer
from app.payin.core.payer.v1.processor import PayerProcessorV1

api_tags = ["PayerV1"]
router = APIRouter()


@router.post(
    "/payers",
    response_model=Payer,
    status_code=HTTP_201_CREATED,
    operation_id="CreatePayer",
    tags=api_tags,
)
async def create_payer(
    req_body: CreatePayerRequest,
    log: BoundLogger = Depends(get_logger_from_req),
    payer_processor: PayerProcessorV1 = Depends(PayerProcessorV1),
) -> Payer:
    """
    Create a payer on DoorDash payments platform

    - **dd_payer_id**: DoorDash consumer_id, store_id, or business_id
    - **payer_type**: type that specifies the role of payer
    - **email**: payer email
    - **country**: payer country. It will be used by payment gateway provider.
    - **description**: a description of payer
    """
    log.info(
        "[create_payer] receive request.",
        dd_payer_id=req_body.dd_payer_id,
        payer_type=req_body.payer_type,
    )

    # Verify dd_payer_id is numeric if it is provided.
    if req_body.dd_payer_id:
        try:
            int(req_body.dd_payer_id)
        except ValueError:
            log.exception(
                "[create_payer] Value error for non-numeric value.",
                dd_payer_id=req_body.dd_payer_id,
            )
            raise PayinError(error_code=PayinErrorCode.PAYER_CREATE_INVALID_DATA)

    payer: Payer = await payer_processor.create_payer(
        dd_payer_id=req_body.dd_payer_id,
        payer_type=req_body.payer_type,
        email=req_body.email,
        country=req_body.country,
        description=req_body.description,
    )
    log.info("[create_payer] completed.")
    return payer


@router.get(
    "/payers/{payer_id}",
    response_model=Payer,
    status_code=HTTP_200_OK,
    operation_id="GetPayer",
    tags=api_tags,
)
async def get_payer(
    payer_id: UUID,
    force_update: bool = False,
    log: BoundLogger = Depends(get_logger_from_req),
    payer_processor: PayerProcessorV1 = Depends(PayerProcessorV1),
) -> Payer:
    """
    Get payer.

    - **payer_id**: DoorDash payer_id or stripe_customer_id
    - **force_update**: [boolean] specify if requires a force update from Payment Provider (default is "false")
    """
    log.info("[get_payer] received request.", payer_id=payer_id)
    return await payer_processor.get_payer(payer_id=payer_id, force_update=force_update)


@router.post(
    "/payers/{payer_id}/default_payment_method",
    response_model=Payer,
    status_code=HTTP_200_OK,
    operation_id="UpdatePayer",
    tags=api_tags,
)
async def update_default_payment_method(
    payer_id: UUID,
    req_body: UpdatePayerRequestV1,
    log: BoundLogger = Depends(get_logger_from_req),
    payer_processor: PayerProcessorV1 = Depends(PayerProcessorV1),
):
    """
    Update payer's default payment method

    - **default_payment_method**: payer's payment method (source) on authorized Payment Provider
    - **default_payment_method.payment_method_id**: [UUID] identity of the payment method.
    - **default_payment_method.dd_stripe_card_id**: [string] legacy primary id of StripeCard object
    """

    log.info("[update_payer] received request", payer_id=payer_id)
    # verify default_payment_method to ensure only one id is provided
    _verify_payment_method_id(req_body)

    return await payer_processor.update_default_payment_method(
        payer_id=payer_id,
        payment_method_id=req_body.default_payment_method.payment_method_id,
        dd_stripe_card_id=req_body.default_payment_method.dd_stripe_card_id,
    )


def _verify_payment_method_id(request: UpdatePayerRequestV1):
    count: int = 0
    for key, value in request.default_payment_method:
        if value:
            count += 1

    if count != 1:
        raise PayinError(
            error_code=PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE
        )
