import cv2
import numpy as np

classes = None

with open('coco.txt', 'r') as f:
    classes = [line.strip() for line in f.readlines()]

COLORS = np.random.uniform(0, 255, size=(len(classes), 3))

net = cv2.dnn.readNet('yolov4-tiny.weights', 'yolov4-tiny.cfg')


def get_output_layers(net):
    
    layer_names = net.getLayerNames()
    try:
        output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]
    except:
        output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]

    return output_layers


def draw_prediction(img, class_id, confidence, x, y, x_plus_w, y_plus_h):

    label = str(classes[class_id])

    color = COLORS[class_id]

    cv2.rectangle(img, (x,y), (x_plus_w,y_plus_h), color, 2)

    cv2.putText(img, label, (x-10,y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)


def Summary(inp):
    objects = set(inp)
    keys = []
    vals = []
    for obj in objects:
        keys.append(obj)
        vals.append(inp.count(obj))
    return dict(zip(keys, vals))

    

def detect(image):
    Width = image.shape[1]
    Height = image.shape[0]
    scale = 0.00392

    hsl = cv2.cvtColor(image, cv2.COLOR_BGR2HLS)
    Lchanneld = hsl[:, :, 1]
    lvalueld = cv2.mean(Lchanneld)[0]

    blob = cv2.dnn.blobFromImage(image, scale, (416,416), (0,0,0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(get_output_layers(net))
    class_ids = []
    confidences = []
    boxes = []
    conf_threshold = 0.1
    nms_threshold = 0.5
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.1:
                center_x = int(detection[0] * Width)
                center_y = int(detection[1] * Height)
                w = int(detection[2] * Width)
                h = int(detection[3] * Height)
                x = center_x - w / 2
                y = center_y - h / 2
                class_ids.append(class_id)
                confidences.append(float(confidence))
                boxes.append([x, y, w, h])
    indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)
    objects = []
    accuracy = []
    for i in indices:
        try:
            box = boxes[i]
        except:
            i = i[0]
            box = boxes[i]
        x = box[0]
        y = box[1]
        w = box[2]
        h = box[3]
        objects.append(classes[class_ids[i]])
        accuracy.append(round(confidences[i]*100.0, 0))
        draw_prediction(image, class_ids[i], confidences[i], round(x), round(y), round(x+w), round(y+h))
    # print(objects)
    # print(accuracy)
    cv2.putText(image, f'L value: {lvalueld:.2f}', (10, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2, cv2.LINE_AA)
    summary = Summary(objects)
    # cv2.imwrite("image.jpg", image)
    return summary, lvalueld, image



