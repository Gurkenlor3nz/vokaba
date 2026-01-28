# vokaba/ocr_android_mlkit.py
from __future__ import annotations

from typing import Any, Dict, List
from threading import Event

_JAVA: Dict[str, Any] = {}

def warmup_mlkit() -> None:
    global _JAVA
    if _JAVA:
        return
    from jnius import autoclass
    _JAVA = {
        "PythonActivity": autoclass("org.kivy.android.PythonActivity"),
        "File": autoclass("java.io.File"),
        "Uri": autoclass("android.net.Uri"),
        "InputImage": autoclass("com.google.mlkit.vision.common.InputImage"),
        "TextRecognition": autoclass("com.google.mlkit.vision.text.TextRecognition"),
        "TextRecognizerOptions": autoclass("com.google.mlkit.vision.text.latin.TextRecognizerOptions"),
        "Tasks": autoclass("com.google.android.gms.tasks.Tasks"),
        "TimeUnit": autoclass("java.util.concurrent.TimeUnit"),
    }

def mlkit_to_paddle_pages_async(image_path: str, timeout_sec: float = 30.0) -> List[Dict[str, Any]]:
    """
    Startet MLKit OCR auf dem UI-Thread und liefert 'paddle-like' pages zurück.
    Worker-Thread wartet nur auf Event -> vermeidet Crashes durch Java-Calls aus Background-Threads.
    """
    if not image_path:
        raise RuntimeError("MLKit OCR: image_path is empty")

    done = Event()
    state: Dict[str, Any] = {"pages": None, "err": None, "_keep": None}

    try:
        from android.runnable import run_on_ui_thread
    except Exception:
        # Fallback: wenn run_on_ui_thread nicht da ist, nutze die sync-Variante (kann auf manchen Geräten crashen)
        from .ocr_android_mlkit import mlkit_to_paddle_pages  # type: ignore
        return mlkit_to_paddle_pages(image_path)

    from jnius import PythonJavaClass, java_method

    @run_on_ui_thread
    def _start_on_ui():
        try:
            warmup_mlkit()

            PythonActivity = _JAVA["PythonActivity"]
            File = _JAVA["File"]
            Uri = _JAVA["Uri"]
            InputImage = _JAVA["InputImage"]
            TextRecognition = _JAVA["TextRecognition"]
            TextRecognizerOptions = _JAVA["TextRecognizerOptions"]

            activity = PythonActivity.mActivity
            ctx = activity.getApplicationContext()

            uri = Uri.fromFile(File(image_path))
            image = InputImage.fromFilePath(ctx, uri)

            recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
            task = recognizer.process(image)

            class _Success(PythonJavaClass):
                __javainterfaces__ = ["com/google/android/gms/tasks/OnSuccessListener"]
                __javacontext__ = "app"

                @java_method("(Ljava/lang/Object;)V")
                def onSuccess(self, result):  # result = com.google.mlkit.vision.text.Text
                    try:
                        rec_texts: List[str] = []
                        rec_scores: List[float] = []
                        dt_boxes: List[List[float]] = []

                        blocks = result.getTextBlocks()
                        for bi in range(blocks.size()):
                            block = blocks.get(bi)
                            lines = block.getLines()
                            for li in range(lines.size()):
                                line = lines.get(li)
                                txt = str(line.getText() or "").strip()
                                if not txt:
                                    continue
                                bb = line.getBoundingBox()
                                if bb is None:
                                    continue
                                rec_texts.append(txt)
                                rec_scores.append(0.99)
                                dt_boxes.append([float(bb.left), float(bb.top), float(bb.right), float(bb.bottom)])

                        state["pages"] = [{"res": {"rec_texts": rec_texts, "rec_scores": rec_scores, "dt_boxes": dt_boxes}}]
                    except Exception as e:
                        state["err"] = f"MLKit OCR parse failed: {e}"
                    finally:
                        try:
                            recognizer.close()
                        except Exception:
                            pass
                        done.set()

            class _Failure(PythonJavaClass):
                __javainterfaces__ = ["com/google/android/gms/tasks/OnFailureListener"]
                __javacontext__ = "app"

                @java_method("(Ljava/lang/Exception;)V")
                def onFailure(self, e):
                    try:
                        state["err"] = f"MLKit OCR failed: {e}"
                    except Exception:
                        state["err"] = "MLKit OCR failed"
                    finally:
                        try:
                            recognizer.close()
                        except Exception:
                            pass
                        done.set()

            success = _Success()
            failure = _Failure()

            # wichtig: Referenzen halten, sonst GC bevor Callback feuert
            state["_keep"] = (success, failure, recognizer, task)

            task.addOnSuccessListener(success)
            task.addOnFailureListener(failure)

        except Exception as e:
            state["err"] = f"MLKit init failed: {e}"
            done.set()

    _start_on_ui()

    if not done.wait(timeout_sec):
        raise RuntimeError(f"MLKit OCR timeout after {timeout_sec}s")

    if state.get("err"):
        raise RuntimeError(state["err"])

    pages = state.get("pages")
    if not pages:
        raise RuntimeError("MLKit OCR returned no text.")
    return pages
