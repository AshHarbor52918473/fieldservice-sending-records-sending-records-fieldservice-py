from src.fieldservice_records import WorkOrder, dispatch_decision


def test_completed_order_with_photo_moves_to_customer_follow_up() -> None:
    order = WorkOrder("WO-1", "Ari", "completed", ("photo-1",), "send summary")
    assert dispatch_decision(order) == "ready_for_customer_follow_up"


def test_completed_order_without_photo_stays_with_technician() -> None:
    order = WorkOrder("WO-2", "Ari", "completed", (), "capture evidence")
    assert dispatch_decision(order) == "needs_technician_follow_up"
