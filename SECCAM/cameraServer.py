from flask import Flask, render_template, Response, request, jsonify
import cv2
import threading

#import datetime
from datetime import datetime
app = Flask(__name__)
cam = cv2.VideoCapture(0)
cam2 = cv2.VideoCapture(1)
import os
import shutil
import time
import json
import platform

from gtts import gTTS


########### SETUP CODE ##########

#body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_fullbody.xml')
body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
image = None
captured_images = 0
smart_security = False
human_count = 0

font2 = cv2.FONT_HERSHEY_DUPLEX
fourcc = cv2.VideoWriter_fourcc(*'XVID')


def record_clip(rec_frame, out):    
    rec_frame = cv2.resize(rec_frame, (640,480)) #resize original frame
    out.write(rec_frame)   

def relaunch(video_count):
    print("system relaunch #" + str(video_count))        
    out = cv2.VideoWriter("rec_" + str(video_count) + ".mp4", fourcc, 20.0, (640,  480)) #save clip to current directory
    print("* * * * * * * * VIDEO complete * * * * * ")
    return out


def analysis():

    some_motion = False
    already_played_audio = False
    video_count=0
    count = 0
    out = relaunch(video_count)

    
    while True:
        ret, frame1 = cam.read()
        ret, frame2 = cam.read()

        y= datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame1, "TIME:  " + str(y) , (50, 50), font2, 1, (255,255,255) , 2)

        ## Motion analysis
        diff = cv2.absdiff(frame1, frame2)
        gray = cv2.cvtColor(diff, cv2.COLOR_RGB2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=3)
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours:
            
            if cv2.contourArea(c) > 20000: 
                some_motion = True
                print("[!] Motion triggered")
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(frame1, (x, y), (x+w, y+h), (0, 255, 0), 2)
   
                if(already_played_audio == False):
                    os.system("ok.mp3")
                    already_played_audio = True
                break

        ##If detected motion once, then start recording...
        if some_motion == True:
            if count<75:
                record_clip(frame1,out)             
                count = count + 1

            else:  ## ONCE CLIP IS DONE!!!
                print("[DONE] Recording Done")            
                already_played_audio = False
                some_motion = False
                count = 0
                video_count = video_count + 1               
                
                new_out = relaunch(video_count)                
                out = new_out

                ## Move the file from current directory into static folder for server filehosting
                src = r"C:\Users\Sri\Desktop\SECCAM\rec_"+ str(video_count-1) + ".mp4"
                dest = r"C:\Users\Sri\Desktop\SECCAM\static"                
                try:
                    shutil.move(src,dest)
                except:
                    print('[IGNORE THIS] file redundant error')

        
        cv2.imshow('Transmit frame', frame1)
        global image
        image = frame1
        if cv2.waitKey(10) == ord('q'):
            break 



##############################
# new thread for "motion detection for camera 1 only (outdoor camera)"
thread_motion_detection = threading.Thread(target=analysis)
thread_motion_detection.start()
#############################

@app.route('/')
def index():    
     return render_template('index.html')
    
@app.route('/repl')
def repl():
    print('ajax call starting')

    final_json = "\"files\":"
    final_json = "{"+ final_json + "["
    ret_array = []
    arr = os.listdir("C:/Users/Sri/Desktop/SECCAM/static")
    for file in arr:
        if file.endswith('mp4'):
            ret_array.append(file)

    for name in ret_array:
        final_json = final_json + "{\"filename\" : "
        final_json = final_json + "\"" + name + "\"" + ","
        
        x = os.path.getctime("C:/Users/Sri/Desktop/SECCAM/static/"+name)
        cdate = datetime.fromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S')
        final_json = final_json + "\"datecreated\" : "
        final_json = final_json + "\"" + cdate + "\"" + "},"

    final_json = final_json[:-1]
    final_json = final_json + "]}"

    print(final_json)
    y = json.loads(final_json)
    print("----------------")
   
    return jsonify(y)  

# Stream camera 1 feed
def gen(video):
    while True:        
        global image        
        ret, jpeg = cv2.imencode('.jpg', image)
        frame = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
        
# Render camera 1 feed in HTML
@app.route('/video_feed')
def video_feed():
    global cam
    return Response(gen(cam),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Process camera 2 feed (Look for humans)
def gen2():
    while True:
        ret, frame_2 = cam2.read()
        gray = cv2.cvtColor(frame_2, cv2.COLOR_BGR2GRAY)  
        persons_detected = body_cascade.detectMultiScale(gray, 1.3, 5)
        global human_count
        try:
            human_count = persons_detected.shape[0]
        except:
            human_count = 0

        for (x, y, w, h) in persons_detected:
            cv2.rectangle(frame_2, (x,y), (x+w, y+h), (0, 255, 0), 2)

        ## If human detected, will take a picture and copy to 
        if(human_count > 0):
            global captured_images
            cv2.imwrite('images/human_face' + str(captured_images) + '.png',frame_2)
            captured_images = captured_images + 1

        cv2.putText(frame_2, "Living room camera" , (50, 50), font2, 1, (255,255,255) , 2)
        cv2.putText(frame_2, "# Occuapants: " + str(human_count) , (50, 450), font2, 1, (255,255,255) , 2)
 
        #for (x, y, w, h) in faces:
          #  cv2.rectangle(frame_2, (x, y), (x+w, y+h), (0, 255, 0), 2)
   
        cv2.imshow('Human Detection', frame_2)
        
        ret, jpeg_2 = cv2.imencode('.jpg', frame_2)
        display_frame = jpeg_2.tobytes()
        
        if cv2.waitKey(10) == ord('q'):
            break
        yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + display_frame + b'\r\n\r\n')    

# Render camera 2 feed in HTML
@app.route('/video_feed2')
def video_feed2():
    
##############################
    thread_cam2= threading.Thread(target=gen2)
    thread_cam2.start()
#############################
    return Response(gen2(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Actions for the 3 buttons on server webpage (HTML)

# This method runs when  "ON" button pressed on webpage
@app.route('/button_on')
def button_on():
    print("button ON triggered")
    global smart_security
    smart_security = True    
    os.system("on.mp3")
    return ('', 204)

# This method runs when  "OFF" button pressed on webpage
@app.route('/button_off')
def button_off():
    print("button OFF triggered")
    global smart_security
    smart_security = False
    os.system("off.mp3")
    return ('', 204)

# This method runs when  "STATUS" button pressed on webpage
# Will read aloud on/off status and how many people in the living room
@app.route('/status')
def status():
    print('S.S.S. system readout initialized')   
    say = "STATUS." + "Currently," + str(human_count)+ "people in the living room."    

    if smart_security:
        say = say + "SMART monitoring is ONLINE"
    else:
        say = say + "SMART monitoring is OFFLINE"

    myobj = gTTS(text=say , slow=False, lang = 'en-uk')
    myobj.save("status.mp3")
    os.system("status.mp3")
    return ('', 204)

# REPLACE IP ADDRESS with your computer ip address
if __name__ == '__main__':
    app.run(host='192.168.1.6', port=8000, threaded=True)





