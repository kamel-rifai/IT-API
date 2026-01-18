from fastapi import FastAPI, HTTPException, Depends, status, Request
from pydantic import BaseModel
from typing_extensions import Annotated
from typing import Optional
import models
from db import engine, session
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from datetime import date, datetime, timedelta
from secret import SECRET_KEY, ALGO
from re import findall
from icmplib  import ping , Host
import os
import asyncio
from icmplib import async_ping



app = FastAPI()

SECRET_KEY = SECRET_KEY
ALGORITHM = ALGO
ACCESS_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

models.Base.metadata.create_all(bind=engine)

class DeviceBase(BaseModel):
    type:str
    name:str
    model:str
    floor:int
    place:str
    cableNumber:Optional[str]
    Mac:Optional[str]
    IP:Optional[str]
    Notes:Optional[str] 
    show:bool
    active:bool

class DeviceUpdate(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = None
    model: Optional[str] = None
    floor: Optional[int] = None
    place: Optional[str] = None
    cableNumber: Optional[str] = None
    Mac: Optional[str] = None
    IP: Optional[str] = None
    Notes: Optional[str] = None
    show: Optional[bool] = None
    active: Optional[bool] = None

class CameraBase(BaseModel):
    type:str
    model:str
    place:str
    cableNumber:Optional[str]
    Mac:Optional[str]
    IP:Optional[str]
    Notes:Optional[str] 
    show:bool
    Date:str

class TeloBase(BaseModel):
    type:str
    model:str
    place:str
    Mac:Optional[str]
    IP:Optional[str]
    Notes:Optional[str] 
    show:bool
    Date:str

class AccessPointBase(BaseModel):
    type:str
    model:str
    place:str
    Mac:Optional[str]
    IP:Optional[str]
    Notes:Optional[str] 
    show:bool
    Date:str

class CabinetBase(BaseModel):
    type:str
    model:str
    place:str
    Notes:Optional[str] 
    show:bool
    Date:str

class SwitchBase(BaseModel):
    type:str
    total_ports:int
    name:str
    model:str
    floor:int
    place:str
    Mac:Optional[str]
    IP:Optional[str]
    Notes:Optional[str] 
    show:bool
    active:bool

class PatchPanelBase(BaseModel):
    title:str
    show:bool

class PortBase(BaseModel):
    number:int
    type:str
    occupied:bool
    device_id:int

class PortUpdate(BaseModel):
    number: Optional[int] = None
    type: Optional[str] = None
    occupied: Optional[bool] = None
    device_id: Optional[int] = None


def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()   

db_dependency = Annotated[Session, Depends(get_db)]

#fetch Api routes ---------------------------------------

@app.get("/devices", status_code=status.HTTP_200_OK)
async def full_fetch(db: db_dependency):

    devices = db.query(models.Devices).all()
    switches = db.query(models.Switches).all()
    patch_panels = db.query(models.PatchPanels).all()
    """if not devices:
        raise HTTPException(status_code=404, detail='There are no devices to show!')

    # --- This is the performant way ---

    # 1. Create a list of "ping" tasks to run
    tasks = []
    devices_to_check = [] # Keep track of which device matches which task
    for device in devices:
        if device.IP:
            tasks.append(async_ping(device.IP, count=1, timeout=0.5 , privileged=False  ))
            devices_to_check.append(device)
        else:
            # Handle devices with no IP
            device.active = False
            device.show = False 

    # 2. Run all ping tasks in parallel
    # asyncio.gather runs all tasks concurrently and waits for them to finish
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 3. Process the results
    for device, res in zip(devices_to_check, results):
        if isinstance(res, Exception) or not res.is_alive:
            # Ping failed (timeout or error)
            if device.active != False:
                device.active = False
        else:
            # Ping succeeded!
            if device.active != True:
                device.active = True
                device.show = True
    
    # 4. Commit all changes to the database ONCE
    db.commit()
    # ------------------------------------
""" 
    print(devices)
    print(switches)
    print(patch_panels)
    return {
    "devices": [
        {
        "id": d.id,
        "name": d.name,
        "IP": d.IP,
        "active": d.active,
        "show": d.show,
        "type": d.type,
        "model": d.model,
        "place": d.place,
        "cableNumber": d.place,
        "Mac": d.Mac,
        "Notes": d.Notes,
        "floor": d.floor,
        "Date": d.Date,
    }
    for d in devices
    ],"switches":[
        {
        "id": s.id,
        "name": s.name,
        "IP": s.IP,
        "active": s.active,
        "show": s.show,
        "type": s.type,
        "model": s.model,
        "place": s.place,
        "Mac": s.Mac,
        "Notes": s.Notes,
        "floor": s.floor,
    }
    for s in switches
],"patchpanels":[
    {
        "id": p.id,
        "title": p.title,
        "unique_id": p.unique_id,
        "show": p.show,
        "ports": p.ports
    }
    for p in patch_panels
    ]}
    
#--- this code is just for the process of adding devices to our database
@app.post("/add", status_code=status.HTTP_201_CREATED)
def add(db:db_dependency, device:DeviceBase):
        db_device = models.Devices(**device.__dict__, Date=datetime.now())
        db.add(db_device)
        db.commit()


@app.put("/edit/{id}", status_code=status.HTTP_200_OK)
def edit(db:db_dependency, id:int, device:DeviceUpdate):
    db_device = db.query(models.Devices).filter(models.Devices.id == id).first()
    if db_device is None:
        raise HTTPException(status_code=404 , detail='Device not found')

    update_data = device.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_device, key, value)
    
    db.commit()
    db.refresh(db_device)
    return db_device


@app.post("/add/patchpanel", status_code=status.HTTP_201_CREATED)
def add_patch_panel(db:db_dependency, patch_panel:PatchPanelBase):
    try:
        db_patch_panel = models.PatchPanels(**patch_panel.__dict__)
        db.add(db_patch_panel)
        db.commit()
        db.refresh(db_patch_panel)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Patch panel already exists")

    patch_panel_ports = [models.PatchPanelPorts(port_number=i, patch_panel_id=db_patch_panel.id, title=f"{db_patch_panel.title}-{i}") for i in range(1, 25)]
    db.add_all(patch_panel_ports)
    db.commit()
    return db_patch_panel

@app.post("/add/switch", status_code=status.HTTP_201_CREATED)
def add_switch(db:db_dependency, switch:SwitchBase):
    try:
        db_switch = models.Switches(**switch.__dict__)
        db.add(db_switch)
        db.commit()
        db.refresh(db_switch)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Switch with same unique fields already exists")
    ports = [models.Ports(port_number=i, switch_id=db_switch.id) for i in range(1, db_switch.total_ports + 1)]
    db.add_all(ports)
    db.commit()
    return db_switch

@app.put("/edit/patchpanel/{id}", status_code=status.HTTP_200_OK)
def edit_patch_panel(db:db_dependency, id:int, patch_panel:PatchPanelBase):
    db_patch_panel = db.query(models.PatchPanels).filter(models.PatchPanels.id == id).first()
    if db_patch_panel is None:
        raise HTTPException(status_code=404 , detail='Patch Panel not found')

    for key, value in patch_panel.__dict__.items():
        setattr(db_patch_panel, key, value)
    
    db.commit()
    db.refresh(db_patch_panel)
    return db_patch_panel

@app.put("/edit/switch/{id}", status_code=status.HTTP_200_OK)
def edit_switch(db:db_dependency, id:int, switch:SwitchBase):
    db_switch = db.query(models.Switches).filter(models.Switches.id == id).first()
    if db_switch is None:
        raise HTTPException(status_code=404 , detail='Switch not found')

    for key, value in switch.__dict__.items():
        setattr(db_switch, key, value)
    
    db.commit()
    db.refresh(db_switch)
    return db_switch

@app.put("/edit/patchpanel/{id}", status_code=status.HTTP_200_OK)
def edit_patch_panel(db:db_dependency, id:int, patch_panel:PatchPanelBase):
    db_patch_panel = db.query(models.PatchPanels).filter(models.PatchPanels.id == id).first()
    if db_patch_panel is None:
        raise HTTPException(status_code=404 , detail='Patch Panel not found')

    for key, value in patch_panel.__dict__.items():
        setattr(db_patch_panel, key, value)
    
    db.commit()
    db.refresh(db_patch_panel)
    return db_patch_panel


    
#this code is just for running the fastapi project without trying to use uvicorn from the terminal .... :)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3666,
        log_level="debug",
        reload=True,
    )