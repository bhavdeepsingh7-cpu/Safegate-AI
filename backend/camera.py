import cv2


class Camera:
    """Handles the webcam connection and frame capture."""

    def __init__(self, camera_index: int = 0):
        self.camera = cv2.VideoCapture(camera_index)

        if not self.camera.isOpened():
            raise RuntimeError("SafeGate could not open the camera.")

    def read(self):
        """Return one camera frame."""

        success, frame = self.camera.read()

        if not success:
            raise RuntimeError("SafeGate could not read a camera frame.")

        return frame

    def release(self) -> None:
        """Release the webcam."""

        self.camera.release()