"""Normalized drag-to-select HUD calibration, independent of screen resolution."""
import cv2
from PySide6.QtCore import Qt,QRectF,Signal,QSize
from PySide6.QtGui import QImage,QPainter,QPen,QColor
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QComboBox,QPushButton,QLabel,QWidget
from .vision import ROI_NAMES

class RegionCanvas(QWidget):
    changed=Signal(list)
    def __init__(self,image,rois,parent=None):
        super().__init__(parent)
        self.image=image;self.rois=dict(rois);self.name="speed";self.start=None;self.end=None
        self.setMinimumSize(640,360)
    def sizeHint(self):return QSize(960,540)
    def image_rect(self):
        h,w=self.image.shape[:2];scale=min(self.width()/w,self.height()/h)
        return QRectF((self.width()-w*scale)/2,(self.height()-h*scale)/2,w*scale,h*scale)
    def normalized(self,point):
        r=self.image_rect();return [max(0,min(1,(point.x()-r.x())/r.width())),max(0,min(1,(point.y()-r.y())/r.height()))]
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton and self.image_rect().contains(event.position()):self.start=self.normalized(event.position());self.end=self.start;self.update()
    def mouseMoveEvent(self,event):
        if self.start:self.end=self.normalized(event.position());self.update()
    def mouseReleaseEvent(self,event):
        if self.start:
            end=self.normalized(event.position());roi=[min(self.start[0],end[0]),min(self.start[1],end[1]),max(self.start[0],end[0]),max(self.start[1],end[1])]
            self.start=self.end=None
            if roi[2]-roi[0]>.005 and roi[3]-roi[1]>.005:self.rois[self.name]=roi;self.changed.emit(roi)
            self.update()
    def paintEvent(self,event):
        painter=QPainter(self);r=self.image_rect();h,w=self.image.shape[:2]
        image=QImage(self.image.data,w,h,self.image.strides[0],QImage.Format_BGR888)
        painter.drawImage(r,image)
        rois=dict(self.rois)
        if self.start:rois[self.name]=[min(self.start[0],self.end[0]),min(self.start[1],self.end[1]),max(self.start[0],self.end[0]),max(self.start[1],self.end[1])]
        for name,(x1,y1,x2,y2) in rois.items():
            painter.setPen(QPen(QColor("#48d89b" if name==self.name else "#2f9bff"),2))
            box=QRectF(r.x()+x1*r.width(),r.y()+y1*r.height(),(x2-x1)*r.width(),(y2-y1)*r.height())
            painter.drawRect(box);painter.drawText(box.topLeft(),name)
        painter.end()

class CalibrationDialog(QDialog):
    def __init__(self,image,rois,proposals=None,parent=None):
        super().__init__(parent);self.setWindowTitle("HUD and track calibration");self.resize(1000,720)
        layout=QVBoxLayout(self)
        instructions=QLabel("Select a field, then drag tightly around it. For speed/gear/lap timer/lap number include only that value.\nRoad sample: clear asphalt away from bike, markings and shadows. Road search: visible track. Bike anchor: small box at the rear tire contact point. Minimap: whole map.")
        instructions.setWordWrap(True);layout.addWidget(instructions)
        self.canvas=RegionCanvas(image,rois,self);layout.addWidget(self.canvas,1)
        row=QHBoxLayout();self.field=QComboBox();self.field.addItems(ROI_NAMES)
        self.field.currentTextChanged.connect(self.choose);row.addWidget(self.field)
        remove=QPushButton("Clear selected region");remove.clicked.connect(self.clear);row.addWidget(remove)
        auto=QPushButton("Use labelled HUD proposals");auto.setEnabled(bool(proposals));auto.clicked.connect(lambda:self.apply_proposals(proposals));row.addWidget(auto)
        layout.addLayout(row)
        self.coordinates=QLabel();self.canvas.changed.connect(lambda roi:self.coordinates.setText(str([round(x,4) for x in roi])));layout.addWidget(self.coordinates)
        buttons=QHBoxLayout();save=QPushButton("Save calibration");save.clicked.connect(self.accept);buttons.addWidget(save)
        cancel=QPushButton("Cancel");cancel.clicked.connect(self.reject);buttons.addWidget(cancel);layout.addLayout(buttons)
    def choose(self,name):self.canvas.name=name;self.canvas.update()
    def clear(self):self.canvas.rois.pop(self.canvas.name,None);self.canvas.update()
    def apply_proposals(self,proposals):self.canvas.rois.update(proposals);self.canvas.update()
