import cv2
import time
import paho.mqtt.client as mqtt
import mysql.connector
from datetime import datetime

# URL kamera ponsel
url = "http://192.168.249.81:8080/video"

# MQTT Broker
mqtt_broker = "broker.hivemq.com"
mqtt_topic = "home/motion"

def save_to_mysql(message):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            port=3307,
            user="root",
            password="",  
            database="iot"  
        )
        cursor = conn.cursor()

        query = "INSERT INTO motion_detectors (date_data, message) VALUES (%s, %s)"
        data = (datetime.now(), message)
        cursor.execute(query, data)
        conn.commit()
        print("Data berhasil disimpan ke database.")
    except mysql.connector.Error as e:
        print(f"Error: Tidak dapat menyimpan data ke MySQL: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# MQTT setup
try:
    client = mqtt.Client()
    client.connect(mqtt_broker, 1883, 60)
    print("Berhasil terhubung ke MQTT Broker")
except Exception as e:
    print(f"Error: Tidak dapat terhubung ke broker MQTT: {e}")
    exit()

# Buka video stream
cap = cv2.VideoCapture(url)
if not cap.isOpened():
    print("Error: Tidak dapat membuka video stream. Periksa URL kamera Anda.")
    exit()

_, frame1 = cap.read()
_, frame2 = cap.read()

# Timer untuk membatasi pengiriman pesan MQTT
last_sent = time.time()
cooldown = 1  # Kirim pesan setiap 5 detik jika deteksi gerakan berulang

while cap.isOpened():
    diff = cv2.absdiff(frame1, frame2)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
    dilated = cv2.dilate(thresh, None, iterations=3)
    contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    motion_detected = False
    for contour in contours:
        if cv2.contourArea(contour) < 1000:
            continue
        motion_detected = True
        # Gambar kotak pada area yang terdeteksi gerakan
        (x, y, w, h) = cv2.boundingRect(contour)
        cv2.rectangle(frame1, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # Kirim pesan MQTT dan simpan ke database jika gerakan terdeteksi
    if motion_detected and time.time() - last_sent > cooldown:
        try:
            client.publish(mqtt_topic, "Motion Detected")
            print("Motion Detected - Pesan dikirim ke MQTT")

            # Simpan pesan ke database
            save_to_mysql("Motion Detected")
            last_sent = time.time()
        except Exception as e:
            print(f"Error: Gagal mengirim pesan atau menyimpan data: {e}")

    # Tampilkan frame video
    cv2.imshow("Motion Detector", frame1)
    frame1 = frame2
    ret, frame2 = cap.read()

    # Periksa jika tidak ada frame baru
    if not ret:
        print("Error: Tidak ada frame baru dari video stream.")
        break

    # Keluar jika tombol 'Esc' ditekan
    if cv2.waitKey(10) == 27:
        print("Keluar dari aplikasi.")
        break

cap.release()
cv2.destroyAllWindows()
