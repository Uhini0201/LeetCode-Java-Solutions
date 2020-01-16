import inspect
from uuid import uuid4

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import build_req_context
from app.payout.core.transfer.processors.monitor_transfer_with_incorrect_status import (
    MonitorTransferWithIncorrectStatus,
    MonitorTransferWithIncorrectStatusRequest,
)
from app.payout.core.transfer.tasks.base_task import BaseTask, normalize_task_arguments
from app.payout.models import PayoutTask
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository


class MonitorTransferWithIncorrectStatusTask(BaseTask):
    def __init__(self, start_time: str):
        self.topic_name = "payment_payout"
        self.task_type = PayoutTask.MONITOR_TRANSFER_WITH_INCORRECT_STATUS
        max_retries: int = 5
        attempts: int = 0
        fn_args: list = []
        super().__init__(
            self.topic_name,
            self.task_type,
            max_retries,
            attempts,
            fn_args,
            normalize_task_arguments(inspect.currentframe()),
        )

    @staticmethod
    async def run(app_context: AppContext, data: dict):
        transfer_repo = TransferRepository(database=app_context.payout_maindb)
        stripe_transfer_repo = StripeTransferRepository(
            database=app_context.payout_maindb
        )
        # convert to monitor transfer with incorrect status
        req_context = build_req_context(
            app_context,
            task_name="MonitorTransferWithIncorrectStatusTask",
            task_id=str(uuid4()),
        )
        monitor_transfer_request_dict = {}
        if "fn_kwargs" in data:
            data_kwargs = data["fn_kwargs"]
            for k, v in data_kwargs.items():
                monitor_transfer_request_dict[k] = v

        monitor_transfer_with_incorrect_status_op_dict = {
            "transfer_repo": transfer_repo,
            "stripe_transfer_repo": stripe_transfer_repo,
            "stripe": req_context.stripe_async_client,
            "logger": req_context.log,
            "kafka_producer": app_context.kafka_producer,
            "request": MonitorTransferWithIncorrectStatusRequest(
                **monitor_transfer_request_dict
            ),
        }
        monitor_transfer_with_incorrect_status_op = MonitorTransferWithIncorrectStatus(
            **monitor_transfer_with_incorrect_status_op_dict
        )
        await monitor_transfer_with_incorrect_status_op.execute()
