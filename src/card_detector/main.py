"""Card detection driver."""
from pathlib import Path

from ultralytics import YOLO

def main() -> None:
    # Load a model
    # model = YOLO("yolov8n.yaml")  # build a new model from scratch
    model = YOLO(Path("models") / "best.pt")  # load a pretrained model (recommended for training)

    # Use the model
    # results = model.train(data="coco128.yaml", epochs=3)  # train the model
    # results = model.val()  # evaluate model performance on the validation set
    results = model("test.jpg")  # predict on an image
    model.export(format="onnx")  # export a model to ONNX format
    print([x for x in results])

if __name__ == "__main__":
    main()
    