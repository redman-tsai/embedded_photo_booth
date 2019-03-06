from picamera.array import PiRGBArray
from picamera import PiCamera
import time
import cv2
import wx
import threading
import string
import random
import requests
import shutil
import os


myEVT_CVSTREAM = wx.NewEventType()
EVT_CVSTREAM = wx.PyEventBinder(myEVT_CVSTREAM)



class FrameEvent(wx.PyCommandEvent):

    def __init__(self, etype, eid, rawframe=None):
        wx.PyCommandEvent.__init__(self, etype, eid)
        self.frame = rawframe

    def GetFrame(self):
        return self.frame


class FrameThread(threading.Thread):

    def __init__(self, parent):
        threading.Thread.__init__(self)
        self.parent = parent
        self.frame = None
        self.camera = PiCamera()
        self.camera.resolution = (parent.capture_w, parent.capture_h)
        self.camera.framerate = parent.capture_fps
        self.rawCapture = PiRGBArray(self.camera, size=(self.parent.capture_w, self.parent.capture_h))

    def run(self):
        for frame in self.camera.capture_continuous(self.rawCapture, format="bgr", use_video_port=True):
            if not self.parent:
                break
            self.frame = frame.array
            evt = FrameEvent(myEVT_CVSTREAM, -1, self.frame)
            wx.PostEvent(self.parent, evt)
            self.rawCapture.truncate(0)
        print("worker termintated")


class MainWindow(wx.Frame):
    capture_w = 600
    capture_h = 480
    capture_fps = 1
    preview_w = 300
    preview_h = 240
    window_w = 620
    window_h = 360
    gaussian_x = 13
    gaussian_y = 9
    movement_thresh = 100
    binary_thresh = 30
    tempdir = "./temp"
    dirip = "http://128.230.210.229:8000/upload"




    def __init__(self, parent, title):
        frame = wx.Frame.__init__(self, parent, title=title, size=(self.window_w, self.window_h))
        # init frames
        camera = PiCamera()
        camera.resolution = (self.capture_w, self.capture_h)
        camera.framerate = self.capture_fps
        rawCapture = PiRGBArray(camera, size=(self.capture_w, self.capture_h))
        camera.capture(rawCapture, format="bgr")
        graygroundraw = cv2.cvtColor(rawCapture.array, cv2.COLOR_BGR2GRAY)
        self.rawback = cv2.GaussianBlur(graygroundraw, (self.gaussian_x, self.gaussian_y), 0)
        self.previous = self.rawback
        rgbcv = cv2.cvtColor(rawCapture.array, cv2.COLOR_BGR2RGB)
        rgbcv = cv2.resize(rgbcv, (self.preview_w, self.preview_h))

        self.photoname = ""


        rawCapture.truncate(0)
        camera.close()

        self.filecount = 0
        self.processed = None
        self.backselect = 0
        self.automode = False
        self.rawimg = None
        time.sleep(0.1)
        self.bmp = wx.Bitmap.FromBuffer(self.preview_w, self.preview_h, rgbcv.tostring())
        self.capbmp = None

        bSizer1 = wx.BoxSizer(wx.VERTICAL)
        self.stbmp1 = wx.StaticBitmap(self, -1, wx.NullBitmap, (10, 10), wx.DefaultSize, 0)
        self.stbmp2 = wx.StaticBitmap(self, -1, wx.NullBitmap, (300, 10), wx.DefaultSize, 0)
        self.stbmp1.SetBitmap(self.bmp)
        bSizer1.Add(self.stbmp1, 0.5, wx.ALIGN_LEFT, 5)
        bSizer1.Add(self.stbmp2, 0.5, wx.ALIGN_RIGHT, 5)

        worker = FrameThread(self)
        worker.start()

        # init window
        self.Center()
        self.CreateStatusBar()
        filemenu = wx.Menu()
        menuAbout = filemenu.Append(wx.ID_ABOUT, "&About", " Information about this program")
        menuExit = filemenu.Append(wx.ID_EXIT, "E&xit", " Terminate the program")
        self.select_auto = wx.CheckBox(self, -1, "Auto", (20, 270))
        self.select_auto.SetValue(False)
        capture_button = wx.Button(self, -1, "Capture", (120, 270))
        select_default_button = wx.Button(self, -1, "True", (220, 270))
        select_back1_button = wx.Button(self, -1, "Forest", (320, 270))
        select_back2_button = wx.Button(self, -1, "Space", (420, 270))
        send_button = wx.Button(self, -1, "Send", (520, 270))

        # Set events
        self.Bind(wx.EVT_CHECKBOX, self.auto_capture, self.select_auto)
        self.Bind(wx.EVT_BUTTON, self.set_default, select_default_button)
        self.Bind(wx.EVT_BUTTON, self.set_back1, select_back1_button)
        self.Bind(wx.EVT_BUTTON, self.set_back2, select_back2_button)
        self.Bind(wx.EVT_BUTTON, self.capture_photo, capture_button)
        self.Bind(wx.EVT_BUTTON, self.sendfile, send_button)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        self.Bind(EVT_CVSTREAM, self.self_refresh)
        self.Show(True)

    def self_refresh(self, e):
        self.rawimg = e.GetFrame()
        self.image_process_cv()
        rgbcv = cv2.cvtColor(self.processed, cv2.COLOR_BGR2RGB)
        rgbcv = cv2.resize(rgbcv, (self.preview_w, self.preview_h))
        self.bmp.CopyFromBuffer(rgbcv.tostring())
        self.stbmp1.SetBitmap(self.bmp)
        print("nextframe")
        self.Refresh()

    def image_process_cv(self):
        gray = cv2.cvtColor(self.rawimg, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (self.gaussian_x, self.gaussian_y), 0)
        movediff = cv2.absdiff(gray, self.previous)
        movemask = cv2.threshold(movediff, self.binary_thresh, 255, cv2.THRESH_BINARY)[1]
        if self.backselect is 0:
            self.processed = self.rawimg
            self.previous = gray
            if self.automode:
                if cv2.countNonZero(movemask) > self.movement_thresh:
                    self.capture()
            return
        framediff = cv2.absdiff(gray, self.rawback)
        framemask = cv2.threshold(framediff, self.binary_thresh, 255, cv2.THRESH_BINARY)[1]
        backgrdpic = "./forest.jpg"
        if self.backselect is 2:
            backgrdpic = "./space.jpg"
        backgroundpic = cv2.imread(backgrdpic)
        backgroundpic = cv2.resize(backgroundpic, (self.capture_w, self.capture_h))
        synthesis_back = cv2.bitwise_and(backgroundpic, backgroundpic, mask=cv2.bitwise_not(framemask))
        synthesis_fore = cv2.bitwise_and(self.rawimg, self.rawimg, mask=framemask)
        self.processed = cv2.bitwise_or(synthesis_back, synthesis_fore)
        self.previous = gray
        if self.automode:
            if cv2.countNonZero(movemask) > self.movement_thresh:
                self.capture()

    def capture_photo(self, e):
        self.capture()

    def capture(self):
        capturename = self.tempdir+"/pic" + str(self.filecount) + ".png"
        self.filecount = self.filecount + 1
        print("captured " + str(self.filecount))
        cv2.imwrite(capturename, self.processed)
        rgbcv = cv2.cvtColor(self.processed, cv2.COLOR_BGR2RGB)
        rgbcv = cv2.resize(rgbcv, (self.preview_w, self.preview_h))
        if self.capbmp is None:
            self.capbmp = wx.Bitmap.FromBuffer(self.preview_w, self.preview_h, rgbcv.tostring())
        else:
            self.capbmp.CopyFromBuffer(rgbcv.tostring())
        self.stbmp2.SetBitmap(self.capbmp)

    def sendfile(self, e):
        size = 10
        chars = string.ascii_uppercase + string.digits
        photoid = ''.join(random.choice(chars) for _ in range(size))
        fname = photoid
        self.select_auto.SetValue(False)
        self.automode = False
        wx.MessageBox('Your Photo ID is :'+ photoid, 'Your Photo ID', wx.OK | wx.ICON_INFORMATION)
        shutil.make_archive(fname, 'zip', self.tempdir)
        fin = open(fname + ".zip", 'rb')
        files = {'file':fin}
        body = {'filename':fname, 'photoid':photoid}
        res = requests.post(self.dirip,  files = files, data =body)
        fin.close()
        shutil.rmtree(self.tempdir)
        os.remove(fname + ".zip")
        os.makedirs(self.tempdir)
        self.filecount = 0


    def auto_capture(self, e):
        if self.select_auto.GetValue():
            self.automode = True
            print("auto capture")
        else:
            self.automode = False
            print("manual capture")

    def set_default(self, e):
        self.backselect = 0
        print("background default")

    def set_back1(self, e):
        self.backselect = 1
        print("background 1")

    def set_back2(self, e):
        self.backselect = 2
        print("background 2")

    def OnAbout(self, e):
        dlg = wx.MessageDialog(self, "Photo Booth", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def OnExit(self, e):
        self.Close(True)


app = wx.App(False)
frame = MainWindow(None, "Photo Booth")
app.MainLoop()
