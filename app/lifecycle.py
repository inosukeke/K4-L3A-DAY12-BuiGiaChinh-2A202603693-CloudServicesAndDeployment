"""Graceful shutdown: bật cờ shutting_down rồi chuyển tiếp cho handler cũ (Uvicorn)."""
import signal

shutting_down = False
_previous_handlers: dict[int, object] = {}


def is_shutting_down() -> bool:
    return shutting_down


def _handle_signal(signum, frame) -> None:
    global shutting_down
    shutting_down = True  # /ready và /health bắt đầu trả 503 để LB ngừng gửi request mới
    previous = _previous_handlers.get(signum)
    if callable(previous):  # SIG_DFL / SIG_IGN không callable nên bỏ qua
        previous(signum, frame)  # để Uvicorn tiếp tục quy trình dừng an toàn


def install_signal_handlers() -> None:
    """Đăng ký handler SIGTERM/SIGINT, nhớ handler cũ để gọi lại."""
    for sig in (signal.SIGTERM, signal.SIGINT):
        current = signal.getsignal(sig)
        if current is _handle_signal:  # tránh lồng handler khi gọi 2 lần
            continue
        _previous_handlers[sig] = current
        signal.signal(sig, _handle_signal)


def reset() -> None:
    global shutting_down
    shutting_down = False
