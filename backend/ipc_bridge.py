# Studio Download - Cross-Thread IPC Bridge for Browser Extension
try:
    from PySide6.QtCore import QObject, Signal

    class ExtensionBridge(QObject):
        remote_stream_received = Signal(dict)
        cookies_updated = Signal(str)

    extension_bridge = ExtensionBridge()
except ImportError:
    class DummyBridge:
        class DummySignal:
            def emit(self, *args, **kwargs):
                pass
            def connect(self, *args, **kwargs):
                pass
        remote_stream_received = DummySignal()
        cookies_updated = DummySignal()

    extension_bridge = DummyBridge()
