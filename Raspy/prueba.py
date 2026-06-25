from picamera2 import Picamera2
import cv2

picam2 = Picamera2()
picam2.start()

imagen = picam2.capture_array()

cv2.imwrite("foto.jpg", imagen)

print("Foto guardada")
