"""Interactive PyQt6 celestial-sphere view for the coordinate converter."""

from __future__ import annotations

import math
from typing import Sequence

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPainterPath, QPen, QPolygonF, QWheelEvent
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .coordinate_converter import equatorial_from_horizontal, horizontal_from_equatorial, parse_degrees, parse_hours
from .theme import NIGHT_BACKGROUND, NIGHT_BORDER, NIGHT_MUTED, NIGHT_TEXT, night_mode_enabled
from .widgets import StringVar

Vector3 = tuple[float, float, float]
Matrix3 = tuple[Vector3, Vector3, Vector3]


def _dot(a: Vector3, b: Vector3) -> float:
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]


def _norm(v: Vector3) -> float:
    return math.sqrt(_dot(v,v))


def _unit(v: Vector3) -> Vector3:
    length=_norm(v)
    if length<1e-12:return (0.0,0.0,0.0)
    return (v[0]/length,v[1]/length,v[2]/length)


def _mat_mul(a: Matrix3,b: Matrix3)->Matrix3:
    return tuple(tuple(sum(a[r][k]*b[k][c] for k in range(3)) for c in range(3)) for r in range(3))  # type: ignore[return-value]


def _mat_vec(m: Matrix3,v: Vector3)->Vector3:
    return (_dot(m[0],v),_dot(m[1],v),_dot(m[2],v))


def _rotation_x(angle:float)->Matrix3:
    c=math.cos(angle);s=math.sin(angle);return ((1,0,0),(0,c,-s),(0,s,c))


def _rotation_z(angle:float)->Matrix3:
    c=math.cos(angle);s=math.sin(angle);return ((c,-s,0),(s,c,0),(0,0,1))


def _default_view_matrix()->Matrix3:
    return _rotation_x(math.radians(-22.0))


def _cross(a:Vector3,b:Vector3)->Vector3:
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def _great_circle_arc(a:Vector3,b:Vector3,samples:int=72)->list[Vector3]:
    a=_unit(a);b=_unit(b);cosine=max(-1.0,min(1.0,_dot(a,b)));angle=math.acos(cosine)
    if angle<1e-8:return [a,b]
    if math.pi-angle<1e-6:
        helper=(0,1,0) if abs(a[1])<.9 else (1,0,0); tangent=_unit(_cross(helper,a))
        return [_unit((math.cos(math.pi*i/samples)*a[0]+math.sin(math.pi*i/samples)*tangent[0],math.cos(math.pi*i/samples)*a[1]+math.sin(math.pi*i/samples)*tangent[1],math.cos(math.pi*i/samples)*a[2]+math.sin(math.pi*i/samples)*tangent[2])) for i in range(samples+1)]
    sine=math.sin(angle);points=[]
    for i in range(samples+1):
        t=i/samples;wa=math.sin((1-t)*angle)/sine;wb=math.sin(t*angle)/sine;points.append((wa*a[0]+wb*b[0],wa*a[1]+wb*b[1],wa*a[2]+wb*b[2]))
    return points


def _circle_in_plane(u:Vector3,v:Vector3,samples:int=144)->list[Vector3]:
    u=_unit(u);v=_unit(v);return [(math.cos(2*math.pi*i/samples)*u[0]+math.sin(2*math.pi*i/samples)*v[0],math.cos(2*math.pi*i/samples)*u[1]+math.sin(2*math.pi*i/samples)*v[1],math.cos(2*math.pi*i/samples)*u[2]+math.sin(2*math.pi*i/samples)*v[2]) for i in range(samples+1)]


def _arc_in_plane(u:Vector3,v:Vector3,start_degrees:float,end_degrees:float,samples:int=64)->list[Vector3]:
    u=_unit(u);v=_unit(v);out=[]
    for i in range(samples+1):
        angle=math.radians(start_degrees+(end_degrees-start_degrees)*i/samples);out.append((math.cos(angle)*u[0]+math.sin(angle)*v[0],math.cos(angle)*u[1]+math.sin(angle)*v[1],math.cos(angle)*u[2]+math.sin(angle)*v[2]))
    return out


class _SphereCanvas(QWidget):
    def __init__(self, owner:"CelestialSphereTriangle") -> None:
        super().__init__(owner); self.owner=owner; self.setMinimumHeight(370); self.setCursor(Qt.CursorShape.SizeAllCursor); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self,_event)->None:  # noqa: N802
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing); self.owner._paint(painter,self.width(),self.height())

    def mousePressEvent(self,event:QMouseEvent)->None:  # noqa: N802
        if event.button()==Qt.MouseButton.LeftButton:self.owner._drag_start(event.position())

    def mouseMoveEvent(self,event:QMouseEvent)->None:  # noqa: N802
        if event.buttons() & Qt.MouseButton.LeftButton:self.owner._drag_move(event.position())

    def mouseReleaseEvent(self,event:QMouseEvent)->None:  # noqa: N802
        if event.button()==Qt.MouseButton.LeftButton:self.owner._drag_end()

    def mouseDoubleClickEvent(self,event:QMouseEvent)->None:  # noqa: N802
        if event.button()==Qt.MouseButton.LeftButton:self.owner.reset_view()

    def wheelEvent(self,event:QWheelEvent)->None:  # noqa: N802
        self.owner._zoom_by(1.08 if event.angleDelta().y()>0 else 1/1.08); event.accept()


class CelestialSphereTriangle(QWidget):
    """Draggable orthographic sphere linked to converter variables."""

    def __init__(self,parent:QWidget|None=None,*,latitude_var:StringVar,ra_var:StringVar,dec_var:StringVar,lst_var:StringVar,ha_var:StringVar,alt_var:StringVar,az_var:StringVar)->None:
        super().__init__(parent)
        self._vars={"latitude":latitude_var,"ra":ra_var,"dec":dec_var,"lst":lst_var,"ha":ha_var,"alt":alt_var,"az":az_var}
        self._observer_transform:Matrix3=((1,0,0),(0,1,0),(0,0,1)); self._view_matrix=_default_view_matrix(); self._zoom=.86; self._drag_origin:QPointF|None=None; self._drag_view:Matrix3|None=None; self._projection=(0.0,0.0,100.0)
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(6)
        title=QLabel("Celestial sphere");title.setObjectName("SectionTitle");layout.addWidget(title)
        self.canvas=_SphereCanvas(self);layout.addWidget(self.canvas)
        row=QHBoxLayout();self.readout=QLabel("Enter values to place ★.");self.readout.setObjectName("Muted");self.readout.setWordWrap(True);row.addWidget(self.readout,1);button=QPushButton("Reset");button.clicked.connect(self.reset_view);row.addWidget(button);layout.addLayout(row)
        for variable in self._vars.values():variable.changed.connect(lambda _value:self.canvas.update())
        self.refresh_theme()

    def reset_view(self)->None:
        self._view_matrix=_default_view_matrix();self._drag_origin=None;self._drag_view=None;self._zoom=.86;self.canvas.update()

    def refresh_theme(self)->None:
        night=night_mode_enabled(self)
        self._palette={
            "background":NIGHT_BACKGROUND if night else "#f7f9fc","border":NIGHT_BORDER if night else "#b8c2cf","sphere":NIGHT_BORDER if night else "#5b6675","back":NIGHT_MUTED if night else "#aeb7c2","equator":"#980000" if night else "#386cb0","horizon":"#d00000" if night else "#1b8a6b","meridian":"#720000" if night else "#7a8796","triangle":"#ff3030" if night else "#7b3fb2","coordinate":"#c00000" if night else "#c56b00","star":NIGHT_TEXT if night else "#b85f00","point":NIGHT_TEXT if night else "#293241","text":NIGHT_TEXT if night else "#202833","muted":NIGHT_MUTED if night else "#66717f",
        };self.canvas.update()

    def _drag_start(self,pos:QPointF)->None:self._drag_origin=QPointF(pos);self._drag_view=self._view_matrix
    def _drag_move(self,pos:QPointF)->None:
        if self._drag_origin is None or self._drag_view is None:return
        dx=pos.x()-self._drag_origin.x();dy=pos.y()-self._drag_origin.y();drag=_mat_mul(_rotation_x(math.radians(-dy*.45)),_rotation_z(math.radians(-dx*.45)));self._view_matrix=_mat_mul(drag,self._drag_view);self.canvas.update()
    def _drag_end(self)->None:self._drag_origin=None;self._drag_view=None
    def _zoom_by(self,factor:float)->None:self._zoom=max(.58,min(1.22,self._zoom*factor));self.canvas.update()

    def _hours(self,name:str,*,signed:bool)->float|None:
        text=self._vars[name].get().strip()
        if not text:return None
        try:return parse_hours(text,signed=signed)
        except ValueError:return None

    def _degrees(self,name:str,minimum:float,maximum:float,*,wrap_360:bool=False)->float|None:
        text=self._vars[name].get().strip()
        if not text:return None
        try:return parse_degrees(text,minimum=minimum,maximum=maximum,label=name.title(),wrap_360=wrap_360)
        except ValueError:return None

    def _rotate(self,point:Vector3)->Vector3:return _mat_vec(self._view_matrix,_mat_vec(self._observer_transform,point))
    def _project(self,point:Vector3)->tuple[float,float,float]:
        x,depth,z=self._rotate(point);cx,cy,r=self._projection;return cx+r*x,cy-r*z,depth

    def _paint(self,painter:QPainter,width:int,height:int)->None:
        p=self._palette;painter.fillRect(QRectF(0,0,width,height),QColor(p["background"]));cx=width*.5;cy=height*.49;radius=max(98.0,min(width*.31,height*.39)*self._zoom);self._projection=(cx,cy,radius)
        painter.setPen(QPen(QColor(p["sphere"]),2));painter.setBrush(Qt.BrushStyle.NoBrush);painter.drawEllipse(QPointF(cx,cy),radius,radius)
        latitude=self._degrees("latitude",-90,90);dec=self._degrees("dec",-90,90);ha=self._hours("ha",signed=True);altitude=self._degrees("alt",-90,90);azimuth=self._degrees("az",0,360,wrap_360=True)
        if latitude is None:
            self._observer_transform=((1,0,0),(0,1,0),(0,0,1));self._draw_polyline(painter,_circle_in_plane((1,0,0),(0,1,0)),p["equator"],p["back"],1.5);self._draw_point(painter,(0,0,1),"P","NCP");self._draw_point(painter,(0,0,-1),"","");self._draw_center_message(painter,"Enter latitude.");self.readout.setText("Enter latitude.");return
        if (dec is None or ha is None) and altitude is not None and azimuth is not None:
            try:dec,ha=equatorial_from_horizontal(latitude,altitude,azimuth)
            except ValueError:pass
        if dec is not None and ha is not None and (altitude is None or azimuth is None):
            try:altitude,azimuth=horizontal_from_equatorial(latitude,dec,ha)
            except ValueError:pass
        phi=math.radians(latitude);north=(-math.sin(phi),0.0,math.cos(phi));east=(0.0,1.0,0.0);zenith=(math.cos(phi),0.0,math.sin(phi));pole=(0.0,0.0,1.0);south=(0.0,0.0,-1.0);self._observer_transform=(east,north,zenith)
        self._draw_polyline(painter,_circle_in_plane((1,0,0),(0,1,0)),p["equator"],p["back"],1.5);self._draw_polyline(painter,_circle_in_plane(north,east),p["horizon"],p["back"],1.8);self._draw_polyline(painter,_circle_in_plane((1,0,0),(0,0,1)),p["meridian"],p["back"],1.0)
        self._draw_point(painter,pole,"P","NCP");self._draw_point(painter,south,"","");self._draw_point(painter,zenith,"Z","Zenith");self._draw_reference_label(painter,(1,0,0),"Celestial equator",p["equator"]);self._draw_reference_label(painter,north,"N",p["horizon"]);self._draw_reference_label(painter,east,"E",p["horizon"]);self._draw_reference_label(painter,tuple(-x for x in north),"S",p["horizon"]);self._draw_reference_label(painter,tuple(-x for x in east),"W",p["horizon"])
        if dec is None or ha is None:
            self._draw_center_message(painter,"Add coordinates to place ★.");self.readout.setText("Add coordinates to place ★.");return
        dec_r=math.radians(dec);ha_deg=ha*15;ha_r=math.radians(ha_deg);star=(math.cos(dec_r)*math.cos(ha_r),-math.cos(dec_r)*math.sin(ha_r),math.sin(dec_r))
        triangle=[(pole,zenith,f"90°−φ = {90-latitude:.1f}°"),(pole,star,f"90°−δ = {90-dec:.1f}°"),(zenith,star,f"z = 90°−h = {90-altitude:.1f}°" if altitude is not None else "z = 90°−h")]
        for start,end,label in triangle:
            arc=_great_circle_arc(start,end);self._draw_polyline(painter,arc,p["triangle"],p["back"],3);self._draw_arc_label(painter,arc,label,p["triangle"])
        equator_object=(math.cos(ha_r),-math.sin(ha_r),0.0);h_arc=_arc_in_plane((1,0,0),(0,-1,0),0,ha_deg);self._draw_polyline(painter,h_arc,p["coordinate"],p["back"],2);self._draw_arc_label(painter,h_arc,f"H = {ha:+.2f} h",p["coordinate"],13)
        dec_arc=_great_circle_arc(equator_object,star,38);self._draw_polyline(painter,dec_arc,p["coordinate"],p["back"],2);self._draw_arc_label(painter,dec_arc,f"δ = {dec:+.1f}°",p["coordinate"],13)
        if altitude is not None and azimuth is not None:
            az_r=math.radians(azimuth);foot=tuple(math.cos(az_r)*north[i]+math.sin(az_r)*east[i] for i in range(3));az_arc=_arc_in_plane(north,east,0,azimuth,max(24,int(abs(azimuth)/4)+1));self._draw_polyline(painter,az_arc,p["coordinate"],p["back"],2);self._draw_arc_label(painter,az_arc,f"A = {azimuth:.1f}°",p["coordinate"],13);alt_arc=_great_circle_arc(foot,star,38);self._draw_polyline(painter,alt_arc,p["coordinate"],p["back"],2);self._draw_arc_label(painter,alt_arc,f"h = {altitude:+.1f}°",p["coordinate"],13)
        self._draw_point(painter,star,"★","Object",star=True);self._draw_angle_hint(painter,pole,f"∠P = |H| = {abs(ha_deg):.1f}°");self.readout.setText(f"φ={latitude:+.1f}°   δ={dec:+.1f}°   H={ha:+.2f} h"+(f"   h={altitude:+.1f}°   A={azimuth:.1f}°" if altitude is not None and azimuth is not None else ""))

    def _draw_polyline(self,painter:QPainter,points:Sequence[Vector3],front_color:str,back_color:str,width:float)->None:
        if len(points)<2:return
        projected=[self._project(point) for point in points];current=None;path=QPainterPath()
        def flush(path_obj:QPainterPath,back:bool|None)->None:
            if back is None or path_obj.elementCount()<2:return
            pen=QPen(QColor(back_color if back else front_color),width);pen.setCapStyle(Qt.PenCapStyle.RoundCap);pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            if back:pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen);painter.setBrush(Qt.BrushStyle.NoBrush);painter.drawPath(path_obj)
        for first,second in zip(projected,projected[1:]):
            back=(first[2]+second[2])*.5<-.015
            if current is None:current=back;path=QPainterPath(QPointF(first[0],first[1]));path.lineTo(QPointF(second[0],second[1]))
            elif back==current:path.lineTo(QPointF(second[0],second[1]))
            else:flush(path,current);current=back;path=QPainterPath(QPointF(first[0],first[1]));path.lineTo(QPointF(second[0],second[1]))
        flush(path,current)

    def _draw_point(self,painter:QPainter,point:Vector3,symbol:str,description:str,*,star:bool=False)->None:
        x,y,depth=self._project(point);p=self._palette;r=7 if star else 4;fill=QColor(p["star"] if star else p["point"]);outline=QColor(p["background"] if depth>=0 else p["back"]);painter.setPen(QPen(outline,1));painter.setBrush(fill)
        if star:
            poly=QPolygonF();
            for i in range(10):
                angle=math.radians(-90+i*36);pr=r if i%2==0 else r*.42;poly.append(QPointF(x+pr*math.cos(angle),y+pr*math.sin(angle)))
            painter.drawPolygon(poly)
        else:painter.drawEllipse(QPointF(x,y),r,r)
        if not symbol and not description:return
        label=symbol if not description else f"{symbol}  {description}";dx=10 if x<=self._projection[0] else -10;painter.setPen(QColor(p["text"] if depth>=0 else p["muted"]));font=QFont(self.font());font.setBold(True);painter.setFont(font);rect=QRectF(x+dx-(0 if dx>0 else 160),y-18,160,24);painter.drawText(rect,int((Qt.AlignmentFlag.AlignLeft if dx>0 else Qt.AlignmentFlag.AlignRight)|Qt.AlignmentFlag.AlignVCenter),label)

    def _draw_reference_label(self,painter:QPainter,point:Vector3,text:str,color:str)->None:
        x,y,_=self._project(point);cx,cy,_=self._projection;dx=12 if x<=cx else -12;dy=-12 if y>=cy else 12;painter.setPen(QColor(color));font=QFont(self.font());font.setItalic(True);font.setPointSizeF(max(7.5,font.pointSizeF()-1));painter.setFont(font);rect=QRectF(x+dx-(0 if dx>0 else 140),y+dy-10,140,20);painter.drawText(rect,int(Qt.AlignmentFlag.AlignLeft if dx>0 else Qt.AlignmentFlag.AlignRight),text)

    def _draw_arc_label(self,painter:QPainter,arc:Sequence[Vector3],text:str,color:str,offset:float=10)->None:
        if not arc:return
        x,y,depth=self._project(arc[len(arc)//2]);cx,cy,_=self._projection;vx=x-cx;vy=y-cy;length=math.hypot(vx,vy) or 1;x+=offset*vx/length;y+=offset*vy/length;painter.setPen(QColor(color if depth>=-.05 else self._palette["muted"]));font=QFont(self.font());font.setBold(True);font.setPointSizeF(max(7.5,font.pointSizeF()-1));painter.setFont(font);painter.drawText(QRectF(x-70,y-10,140,20),int(Qt.AlignmentFlag.AlignCenter),text)

    def _draw_angle_hint(self,painter:QPainter,point:Vector3,text:str)->None:
        x,y,_=self._project(point);cx,_,_=self._projection;right=x<=cx;painter.setPen(QColor(self._palette["triangle"]));font=QFont(self.font());font.setItalic(True);font.setPointSizeF(max(7.5,font.pointSizeF()-1));painter.setFont(font);rect=QRectF(x+(18 if right else -158),y+7,140,20);painter.drawText(rect,int(Qt.AlignmentFlag.AlignLeft if right else Qt.AlignmentFlag.AlignRight),text)

    def _draw_center_message(self,painter:QPainter,text:str)->None:
        cx,cy,_=self._projection;painter.setPen(QColor(self._palette["muted"]));font=QFont(self.font());font.setItalic(True);painter.setFont(font);painter.drawText(QRectF(cx-160,cy-35,320,70),int(Qt.AlignmentFlag.AlignCenter) | int(Qt.TextFlag.TextWordWrap),text)
