from detector import PPEDetector


MODEL_PATH = "runs/detect/runs/safegate_ppe/weights/best.pt"


try:
    detector = PPEDetector(
        model_path=MODEL_PATH,
        confidence=0.25,
    )

    print("Detector test passed!")

except FileNotFoundError as error:
    print(error)