from collections import defaultdict
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing_extensions import Annotated
from typing import Optional, List
import models
from db import engine, session
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from datetime import datetime
from secret import SECRET_KEY, ALGO
import asyncio
from icmplib import async_ping
from routeros_api import RouterOsApiPool


app = FastAPI()

# Complaints router (Planka integration)
from complaints.main import router as complaints_router
app.include_router(complaints_router, prefix="/complaints", tags=["complaints"])

SECRET_KEY = SECRET_KEY
ALGORITHM = ALGO
ACCESS_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

models.Base.metadata.create_all(bind=engine)

class DeviceBase(BaseModel):
    type: str
    name: str
    model: str
    floor: int
    place: str
    cableNumber: Optional[str]
    Mac: Optional[str]
    IP: Optional[str]
    Notes: Optional[str]
    show: bool
    active: bool

class DeviceUpdate(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = None
    model: Optional[str] = None
    floor: Optional[int] = None
    place: Optional[str] = None
    cableNumber: Optional[str] = None
    mac: Optional[str] = None
    ip: Optional[str] = None
    notes: Optional[str] = None
    show: Optional[bool] = None
    active: Optional[bool] = None

class CameraBase(BaseModel):
    type: str
    model: str
    place: str
    cable_number: Optional[str]
    mac: Optional[str]
    ip: Optional[str]
    notes: Optional[str]
    show: bool
    date: str

class TeloBase(BaseModel):
    type: str
    model: str
    place: str
    mac: Optional[str]
    ip: Optional[str]
    notes: Optional[str]
    show: bool
    date: str

class AccessPointBase(BaseModel):
    type: str
    model: str
    place: str
    mac: Optional[str]
    ip: Optional[str]
    notes: Optional[str]
    show: bool
    date: str

class CabinetBase(BaseModel):
    type: str
    model: str
    place: str
    notes: Optional[str]
    show: bool
    date: str

class SwitchBase(BaseModel):
    type: str
    total_ports: int
    name: str
    model: str
    floor: int
    place: str
    Mac: Optional[str]
    IP: Optional[str]
    Notes: Optional[str]
    show: bool
    active: bool
    POE: Optional[bool]
    total_fiber_ports: Optional[int]
    ports: Optional[List[dict]] = None
    fiber_ports: Optional[List[dict]] = None

class PatchPanelBase(BaseModel):
    title: str
    unique_id: str
    floor: int
    show: bool
    ports: Optional[List[dict]] = None

class PortBase(BaseModel):
    number: int
    type: str
    occupied: bool
    device_id: int

class PortUpdate(BaseModel):
    number: Optional[int] = None
    type: Optional[str] = None
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
    if not devices:
        raise HTTPException(status_code=404, detail='There are no devices to show!')

    # --- This is the performant way ---

    # 1. Create a list of "ping" tasks to run
    tasks = []
    switches_tasks = []
    devices_to_check = [] # Keep track of which device matches which task
    switches_to_check = [] # Keep track of which switch matches which task
    for device in devices:
        if device.IP:
            tasks.append(async_ping(device.IP, count=1, timeout=0.5 , privileged=False  ))
            devices_to_check.append(device)
        else:
            # Handle devices with no IP
            device.active = False
            device.show = False 

    for switch in switches:
        if switch.IP:
            switches_tasks.append(async_ping(switch.IP, count=1, timeout=0.5 , privileged=False  ))
            switches_to_check.append(switch)
        else:
            switch.active = False
            switch.show = False

    # 2. Run all ping tasks in parallel
    # asyncio.gather runs all tasks concurrently and waits for them to finish
    results = await asyncio.gather(*tasks, return_exceptions=True)
    switch_results = await asyncio.gather(*switches_tasks, return_exceptions=True)

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

    for switch, res in zip(switches_to_check, switch_results):
        if isinstance(res, Exception) or not res.is_alive:
            # Ping failed (timeout or error)
            if switch.active != False:
                switch.active = False
        else:
            # Ping succeeded!
            if switch.active != True:
                switch.active = True
                switch.show = True
    
    # 4. Commit all changes to the database ONCE
    db.commit()
    # ------------------------------------

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
        "cableNumber": d.cableNumber,
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
        "total_ports": s.total_ports,
        "total_fiber_ports": s.total_fiber_ports,
        "POE": s.POE,
        "ports": [
            {
                "id": p.id,
                "port_number": p.port_number,
                "title": p.title,
                "unique_id": p.unique_id,
                "device": p.device,
                "patch_panel_port": {
                    "id": p.patch_panel_port.id,
                    "title": p.patch_panel_port.title,
                    "port_number": p.patch_panel_port.port_number,
                    "cable_number": p.patch_panel_port.cable_number,
                    "cable_length": p.patch_panel_port.cable_length,
                    "function": p.patch_panel_port.function,
                    "patch_panel": {
                        "id": p.patch_panel_port.patch_panel.id,
                        "title": p.patch_panel_port.patch_panel.title
                    } if p.patch_panel_port and p.patch_panel_port.patch_panel else None
                } if p.patch_panel_port else None
            }
            for p in s.ports
        ]
    }
    for s in switches
],"patchpanels":[
    {
        "id": p.id,
        "title": p.title,
        "unique_id": p.unique_id,
        "show": p.show,
        "floor": p.floor,
        "ports": [
            {
                "id": pp.id,
                "title": pp.title,
                "port_number": pp.port_number,
                "cable_number": pp.cable_number,
                "cable_length": pp.cable_length,
                "switch_port": {
                    "id": pp.switch_port.id,
                    "port_number": pp.switch_port.port_number,
                    "switch": {
                        "id": pp.switch_port.switch.id,
                        "name": pp.switch_port.switch.name,
                        "type": pp.switch_port.device.type if pp.switch_port.device else None,
                    } if pp.switch_port and pp.switch_port.switch else None
                } if pp.switch_port else None
            }
            for pp in p.ports
        ]
    }
    for p in patch_panels
    ]}
    
@app.get("/test", status_code=status.HTTP_200_OK)
def test_endpoint(db:db_dependency):
    try:
        print("Test endpoint called")
        devices = db.query(models.Devices).limit(1).all()
        return {"status": "ok", "devices_count": len(devices)}
    except Exception as e:
        print(f"Test error: {e}")
        return {"status": "error", "message": str(e)}

#--- this code is just for the process of adding devices to our database
@app.get("/switches/available-ports")
def get_available_switch_ports(db:db_dependency, floor: Optional[int] = None):
    # Get switch ports that are not connected to any patch panel port
    query = db.query(models.Ports).filter(models.Ports.patch_panel_port == None)
    
    # Filter by floor if provided
    if floor is not None:
        query = query.join(models.Switches).filter(models.Switches.floor == floor)
    
    available_ports = query.all()
    
    return [
        {
            "id": port.id,
            "port_number": port.port_number,
            "title": port.title,
            "switch": {
                "id": port.switch.id,
                "name": port.switch.name,
                "type": "SWITCH",
                "device": {
                    "id": port.device.id,
                    "name": port.device.name,
                    "type" : port.device.type,
                } if port.device else None
            }
        }
        for port in available_ports
    ]

@app.get("/devices/unlinked")
def get_unlinked_devices(db:db_dependency):
    # Get devices that are not connected to any switch port
    unlinked_devices = db.query(models.Devices).filter(models.Devices.port == None).all()
    
    return [
        {
            "id": device.id,
            "name": device.name,
            "type": device.type,
            "model": device.model,
            "place": device.place,
            "cableNumber": device.cableNumber,
            "Mac": device.Mac,
            "IP": device.IP,
            "Notes": device.Notes,
            "floor": device.floor,
            "active": device.active,
            "show": device.show,
            "Date": device.Date
        }
        for device in unlinked_devices
    ]

@app.post("/add/device", status_code=status.HTTP_201_CREATED)
def add(db:db_dependency, device:DeviceBase):
        db_device = models.Devices(**device.__dict__, Date=datetime.now())
        db.add(db_device)
        db.commit()


@app.put("/edit/{id}", status_code=status.HTTP_200_OK)
def edit(db:db_dependency, id:int, device:DeviceUpdate):
    db_device = db.query(models.Devices).filter(models.Devices.id == id).first()
    print(device)
    if db_device is None:
        raise HTTPException(status_code=404 , detail='Device not found')

    update_data = device.model_dump()
    for key, value in update_data.items():
        setattr(db_device, key, value)
    
    db.commit()
    db.refresh(db_device)
    return db_device


@app.post("/add/patchpanel", status_code=status.HTTP_201_CREATED)
def add_patch_panel(db:db_dependency, patch_panel:PatchPanelBase):
    try:
        print(patch_panel)
        # Filter out ports field from dict to avoid SQLAlchemy processing it
        panel_data = {k: v for k, v in patch_panel.__dict__.items() if k != 'ports'}
        
        # Generate unique_id if empty
        if not panel_data.get('unique_id'):
            import uuid
            panel_data['unique_id'] = str(uuid.uuid4())[:8]
        
        print(f"Panel data to create: {panel_data}")
        db_patch_panel = models.PatchPanels(**panel_data)
        db.add(db_patch_panel)
        db.commit()
        db.refresh(db_patch_panel)
        print(f"Patch panel created with ID: {db_patch_panel.id}")
    except IntegrityError as e:
        db.rollback()
        print(f"IntegrityError: {e}")
        raise HTTPException(status_code=409, detail=f"Patch panel already exists: {str(e)}")
    except Exception as e:
        db.rollback()
        print(f"General Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating patch panel: {str(e)}")

    # Create basic patch panel ports
    patch_panel_ports = [models.PatchPanelPorts(port_number=i, patch_panel_id=db_patch_panel.id, title=f"{db_patch_panel.title}-{i}P") for i in range(1, 25)]
    db.add_all(patch_panel_ports)
    db.commit()  # Commit first to get IDs
    
    # Handle port connections if provided in request
    if hasattr(patch_panel, 'ports') and patch_panel.ports:
        # Refresh to get the created ports with IDs
        db.refresh(db_patch_panel)
        
        for port_data in patch_panel.ports:
            if port_data.get('switch_port') and port_data['switch_port'].get('id'):
                # Find the patch panel port by port_number
                pp_port = next((p for p in db_patch_panel.ports if p.port_number == port_data['port_number']), None)
                if pp_port:
                    # Connect to switch port
                    pp_port.switch_port_id = port_data['switch_port']['id']
        
        db.commit()
    
    return db_patch_panel

@app.post("/add/switch", status_code=status.HTTP_201_CREATED)
def add_switch(db:db_dependency, switch:SwitchBase):
    print(switch)
    try:
        # Filter out complex objects that SQLAlchemy can't handle
        switch_data = {k: v for k, v in switch.__dict__.items() if k not in ['ports', 'fiber_ports']}
        db_switch = models.Switches(**switch_data)
        db.add(db_switch)
        db.commit()
        db.refresh(db_switch)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Switch with same unique fields already exists")
    
    # Create all ports first
    ports = [models.Ports(port_number=i, switch_id=db_switch.id , title=f"{db_switch.name}-P{i}") for i in range(1, db_switch.total_ports + 1)]
    print(f"Created {len(ports)} ports for switch {db_switch.name} (IDs: {[p.port_number for p in ports]})")
    
    # If frontend provided ports with devices, connect them
    if switch.ports:
        print(f"Frontend provided {len(switch.ports)} ports with device connections")
        for port_data in switch.ports:
            port_number = port_data.get('port_number')
            device_id = port_data.get('device_id')
            
            print(f"Processing: port_number={port_number}, device_id={device_id}")
            
            if port_number and device_id:
                # Find the port and connect device
                found_port = None
                for port in ports:
                    if port.port_number == port_number:
                        found_port = port
                        break
                
                if found_port:
                    found_port.device_id = device_id
                    print(f"Connected device {device_id} to port {port_number}")
                else:
                    print(f"Port {port_number} not found in created ports (available: {[p.port_number for p in ports]})")
            else:
                print(f"Skipping port data - missing port_number or device_id")
    
    # Create default fiber ports if none provided  
    if not switch.fiber_ports:
        fiber_ports = [models.FiberPorts(port_number=i, switch_id=db_switch.id , title=f"{db_switch.name}-F{i}") for i in range(1, db_switch.total_fiber_ports + 1)]
    else:
        # Use fiber ports from frontend if provided
        fiber_ports = []
        for i, fp_data in enumerate(switch.fiber_ports):
            fiber_port = models.FiberPorts(
                port_number=fp_data.get('port_number', i+1),
                switch_id=db_switch.id,
                title=fp_data.get('title', f"{db_switch.name}-F{fp_data.get('port_number', i+1)}")
            )
            fiber_ports.append(fiber_port)
    
    db.add_all(ports)
    db.add_all(fiber_ports)
    db.commit()
    return db_switch

@app.put("/edit/switch/{id}", status_code=status.HTTP_200_OK)
def edit_switch(db:db_dependency, id:int, switch:SwitchBase):
    db_switch = db.query(models.Switches).filter(models.Switches.id == id).first()
    if db_switch is None:
        raise HTTPException(status_code=404 , detail='Switch not found')

    # Only update direct attributes, skip nested objects and private attributes
    for key, value in switch.__dict__.items():
        if not key.startswith('_') and key not in ['ports', 'fiber_ports']:
            setattr(db_switch, key, value)
    
    db.commit()
    db.refresh(db_switch)
    return db_switch

@app.put("/edit/patchpanel/{id}", status_code=status.HTTP_200_OK)
def edit_patch_panel(db:db_dependency, id:int, patch_panel:PatchPanelBase):
    try:
        db_patch_panel = db.query(models.PatchPanels).filter(models.PatchPanels.id == id).first()
        if db_patch_panel is None:
            raise HTTPException(status_code=404 , detail='Patch Panel not found')
        
        # Update only specific fields directly
        if patch_panel.title is not None:
            db_patch_panel.title = patch_panel.title
        if patch_panel.unique_id is not None:
            db_patch_panel.unique_id = patch_panel.unique_id
        if patch_panel.floor is not None:
            db_patch_panel.floor = patch_panel.floor
        if patch_panel.show is not None:
            db_patch_panel.show = patch_panel.show
        
        db.commit()
        db.refresh(db_patch_panel)
        return db_patch_panel
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/switch/{id}/port/{port_id}")
def update_switch_port(db:db_dependency, id:int, port_id:int, device_id: Optional[int] = None):
    db_switch = db.query(models.Switches).filter(models.Switches.id == id).first()
    if db_switch is None:
        raise HTTPException(status_code=404 , detail='Switch not found')
    
    switch_port = db.query(models.Ports).filter_by(switch_id=id, port_number=port_id).first()
    if switch_port is None:
        raise HTTPException(status_code=404, detail='Switch Port not found')

    if device_id is None:
        # Disconnect device from port
        switch_port.device_id = None
    else:
        # Connect device to port
        device = db.query(models.Devices).filter_by(id=device_id).first()
        if device is None:
            raise HTTPException(status_code=404, detail='Device not found')
        
        # Check if device is already connected to another port
        if device.port:
            raise HTTPException(status_code=409, detail='Device already connected to another port')
        
        switch_port.device_id = device_id
    
    db.commit()
    db.refresh(switch_port)
    
    # Return with device data
    return {
        "id": switch_port.id,
        "port_number": switch_port.port_number,
        "switch_id": switch_port.switch_id,
        "device_id": switch_port.device_id,
        "device": {
            "id": switch_port.device.id,
            "name": switch_port.device.name,
            "type": switch_port.device.type,
            "floor": switch_port.device.floor
        } if switch_port.device else None
    }

@app.post("/patchpanel/{id}/port/{port_id}")
def update_patch_panel_port(db:db_dependency, id:int, port_id:int, switch_port_id: Optional[int] = None, cable_number: Optional[str] = None, cable_length: Optional[str] = None):
    print(f"Updating patch panel port {port_id} for patch panel {id}")
    print(f"Switch port ID: {switch_port_id}")
    print(f"Cable number: {cable_number}")
    print(f"Cable length: {cable_length}")
    db_patch_panel = db.query(models.PatchPanels).filter(models.PatchPanels.id == id).first()
    if db_patch_panel is None:
        raise HTTPException(status_code=404 , detail='Patch Panel not found')
    pp_port = db.query(models.PatchPanelPorts).filter_by(patch_panel_id=id, port_number=port_id).first()
    if pp_port is None:
        raise HTTPException(status_code=404, detail='Patch Panel Port not found')

    if switch_port_id == 0:
        pp_port.switch_port_id = None
    else:
        if switch_port_id is not None:
            switch_port = db.query(models.Ports).filter_by(id=switch_port_id).first()
            if switch_port is None:
                raise HTTPException(status_code=404, detail='Switch Port not found')
            
            if switch_port.patch_panel_port:
                raise HTTPException(status_code=409, detail='Switch Port already taken')
            pp_port.switch_port_id = switch_port_id
    
    # Update cable information if provided
    if cable_number is not None:
        pp_port.cable_number = cable_number
    if cable_length is not None:
        pp_port.cable_length = cable_length
    
    db.commit()
    db.refresh(pp_port)
    return pp_port

def normalize_mac(mac: str) -> str:
    if not mac: return ""
    # Strip everything and rebuild format AA:BB:CC:DD:EE:FF
    clean = "".join(filter(str.isalnum, mac)).upper()
    if len(clean) != 12: return clean # Fallback for weird data
    return ":".join(clean[i:i+2] for i in range(0, 12, 2))

@app.get("/auto/ports/{switch_id}")
def auto_assign_ports(switch_id: int, db: db_dependency):
    # 1. Fetch Switch
    db_switch = db.query(models.Switches).filter(models.Switches.id == switch_id).first()
    if not db_switch:
        raise HTTPException(status_code=404, detail='Switch not found')
    
    # 2. Prepare Lookups
    unassigned_ports_map = {
        str(p.port_number): p 
        for p in db.query(models.Ports).filter(
            models.Ports.switch_id == switch_id, 
            #models.Ports.device_id == None
        ).all()
    }
    
    # --- CRITICAL CHECK ---
    # We query devices, but let's be less restrictive for a second to see what's happening
    devices_in_db = db.query(models.Devices).filter(
        models.Devices.Mac != None,
        models.Devices.model != 'W610W'
    ).all()
    

    unconnected_devs_map = {}
    for d in devices_in_db:
        # Check if the device is actually "unconnected"
        # Using strip() because sometimes DBs store empty strings instead of NULLs
        #if d.port is None or str(d.port).strip() == "":
            unconnected_devs_map[normalize_mac(d.Mac)] = d

    MAC_DEVICES = unconnected_devs_map.keys()
    print(f"DEBUG: Search set contains: {list(MAC_DEVICES)}", len(MAC_DEVICES))
    # DEBUG: Print how many devices were actually loaded into memory
    print(f"Loaded {len(MAC_DEVICES)} unconnected devices from DB.")

    # 3. Connect to Mikrotik
    try:
        api_pool = RouterOsApiPool(
            host=db_switch.IP,
            username="admin",
            password="555288",
            plaintext_login=True
        )
        api = api_pool.get_api()
        resource = api.get_resource('/interface/bridge/host')
        all_hosts = resource.get()
        api_pool.disconnect() 

        print(all_hosts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API Connection Error: {str(e)}")

    # 4. Filter and Group MACs
    IGNORED_PREFIXES = ('D4:01:C3', '18:FD:74', 'C4:AD:34', '74:4D:28', 'DC:2C:6E', '48:8F:5A')
    port_map = defaultdict(list)
    
    for entry in all_hosts:
        raw_port = entry.get('on-interface', '')
        port_num = raw_port.replace('ether', '') if raw_port.startswith('ether') else None
        mac = normalize_mac(entry.get('mac-address', ''))

        if not port_num or not mac:
            continue
            
        if mac.startswith(IGNORED_PREFIXES):
            print(f"DEBUG: Ignoring MAC: {mac}")
            continue
        print(f"DEBUG: Checking MAC: {mac} - Found in DB: {mac in MAC_DEVICES}")

        if mac not in MAC_DEVICES:
            # This is your current headache. 
            # If this prints, the MAC is 100% NOT in the 'unconnected_devs_map'
            continue
            
        port_map[port_num].append(mac)
    print(len(port_map), "ports with connected devices found.")

    # 5. Process Assignments
    assignments_made = 0
    for port_num, macs in port_map.items():
        if len(macs) == 1:
            target_mac = macs[0]
            switch_port = unassigned_ports_map.get(port_num)
            device = unconnected_devs_map.get(target_mac)

            if switch_port and device:
                switch_port.device_id = device.id
                # Update the device record too if needed
                # device.port = port_num 
                assignments_made += 1
                print(f"Match: Port {port_num} -> {device.name}")

    if assignments_made > 0:
        db.commit()
        db.refresh(db_switch)
    
    return {"switches":
        {
        "id": db_switch.id,
        "name": db_switch.name,
        "IP": db_switch.IP,
        "active": db_switch.active,
        "show": db_switch.show,
        "type": db_switch.type,
        "model": db_switch.model,
        "place": db_switch.place,
        "Mac": db_switch.Mac,
        "Notes": db_switch.Notes,
        "floor": db_switch.floor,
        "total_ports": db_switch.total_ports,
        "total_fiber_ports": db_switch.total_fiber_ports,
        "POE": db_switch.POE,
        "ports": [
            {
                "id": p.id,
                "port_number": p.port_number,
                "title": p.title,
                "unique_id": p.unique_id,
                "device": {
                    "id": p.device.id,
                    "name": p.device.name,
                    "type": p.device.type,
                    "model": p.device.model,
                    "IP": p.device.IP,
                    "Mac": p.device.Mac,
                    "floor": p.device.floor,
                    "place": p.device.place
                } if p.device else None
            }
            for p in db_switch.ports
        ]
    }
    }


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