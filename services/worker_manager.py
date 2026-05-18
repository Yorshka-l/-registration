"""QThread Worker 统一生命周期管理。"""

from PySide6.QtCore import QObject, Signal, QThread


class GenericWorker(QThread):
    """通用后台 Worker，执行任意 callable。"""

    finished = Signal(object)  # 返回值
    error = Signal(str)
    log = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            # 注入 log 回调（如果函数接受的话）
            if "log_callback" in self._func.__code__.co_varnames:
                self._kwargs["log_callback"] = self.log.emit
            result = self._func(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n{traceback.format_exc()}")


class WorkerManager(QObject):
    """管理所有后台 Worker 的生命周期。"""

    def __init__(self):
        super().__init__()
        self._workers: dict[str, GenericWorker] = {}

    def start(self, name: str, func, *args, **kwargs) -> GenericWorker:
        """启动命名 Worker，自动清理同名旧 Worker。"""
        self.cancel(name)
        worker = GenericWorker(func, *args, **kwargs)
        self._workers[name] = worker
        worker.finished.connect(lambda _: self._cleanup(name))
        worker.error.connect(lambda _: self._cleanup(name))
        worker.start()
        return worker

    def cancel(self, name: str):
        """取消指定 Worker。"""
        worker = self._workers.pop(name, None)
        if worker and worker.isRunning():
            worker.terminate()
            worker.wait(3000)

    def cancel_all(self):
        """取消所有 Worker。"""
        for name in list(self._workers):
            self.cancel(name)

    def _cleanup(self, name: str):
        self._workers.pop(name, None)

    def is_running(self, name: str) -> bool:
        worker = self._workers.get(name)
        return worker is not None and worker.isRunning()
