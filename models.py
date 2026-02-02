from sqlalchemy import Boolean, String, Column, Integer, Date, ForeignKey, Table, null
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.orm import relationship
from db import Base


class Devices(Base):
    __tablename__ = "DEVICES"

    id= Column(Integer, primary_key=True, index=True)
    type = Column(String(100))
    name = Column(String(100))
    model = Column(String(120))
    floor = Column(Integer)
    place = Column(String(100))
    cableNumber = Column(String(100))
    Mac = Column(String(100))
    IP = Column(String(100))
    Notes = Column(String(120))
    show = Column(Boolean)
    active = Column(Boolean)
    port = relationship('Ports', back_populates='device', uselist=False)
    Date = Column(String(100))

class Switches(Base):
    __tablename__ = "switches"

    id = Column(Integer, primary_key=True, index=True)
    unique_id = Column(String(50), unique=True)
    type = Column(String(100))
    total_ports = Column(Integer, nullable=False)
    name = Column(String(100))
    model = Column(String(120))
    floor = Column(Integer)
    place = Column(String(100))
    Mac = Column(String(100))
    IP = Column(String(100))
    Notes = Column(String(120))
    show = Column(Boolean)
    active = Column(Boolean)
    POE = Column(Boolean)
    total_fiber_ports = Column(Integer)
    fiber_ports = relationship('FiberPorts', back_populates='switch', cascade='all, delete-orphan')
    ports = relationship('Ports', back_populates='switch', cascade='all, delete-orphan')
    created_at = Column(Date, default=datetime.now)
    updated_at = Column(Date, default=datetime.now, onupdate=datetime.now)


switch_patch_panel = Table(
    'switch_patch_panel',
    Base.metadata,
    Column('switch_id', ForeignKey('switches.id'), primary_key=True),
    Column('patch_panel_id', ForeignKey('patchpanels.id'), primary_key=True),
)

class PatchPanels(Base):
    __tablename__ = "patchpanels"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), unique=False)
    unique_id = Column(String(50), unique=True, nullable=True)
    floor = Column(Integer)
    show = Column(Boolean)
    created_at = Column(Date, default=datetime.now)
    updated_at = Column(Date, default=datetime.now, onupdate=datetime.now)

    ports = relationship('PatchPanelPorts', back_populates='patch_panel',
                         cascade='all, delete-orphan')

    switches = relationship('Switches', secondary=switch_patch_panel,
                            back_populates='patch_panels')

Switches.patch_panels = relationship('PatchPanels',
                                     secondary=switch_patch_panel,
                                     back_populates='switches')


class PatchPanelPorts(Base):
    __tablename__ = "patch_panel_ports"
    id = Column(Integer, primary_key=True)
    title = Column(String(100), unique=False, nullable=True)
    port_number = Column(Integer)
    cable_number = Column(String(100))
    cable_length = Column(String(100))
    function = Column(String(100))
    patch_panel_id = Column(Integer, ForeignKey('patchpanels.id'))
    switch_port_id = Column(Integer, ForeignKey('ports.id'), nullable=True, unique=True)

    patch_panel = relationship('PatchPanels', back_populates='ports')
    switch_port = relationship('Ports')

    
class Ports(Base):
    __tablename__ = "ports"

    id = Column(Integer, primary_key=True, index=True)
    unique_id = Column(String(50), unique=True)
    port_number = Column(Integer)
    title = Column(String(100), nullable=True)
    switch_id = Column(Integer, ForeignKey('switches.id'))
    device_id = Column(Integer, ForeignKey('DEVICES.id'), nullable=True, unique=True)
    switch = relationship('Switches', back_populates='ports')
    device = relationship('Devices', back_populates='port')
    patch_panel_port = relationship('PatchPanelPorts', back_populates='switch_port', uselist=False)


    created_at = Column(Date, default=datetime.now)
    updated_at = Column(Date, default=datetime.now, onupdate=datetime.now)

class FiberPorts(Base):
    __tablename__ = "fiber_ports"
    id = Column(Integer, primary_key=True)
    title = Column(String(100), unique=True, nullable=True)
    port_number = Column(Integer)
    switch_id = Column('fiber_id', Integer, ForeignKey('switches.id'))
    switch = relationship('Switches', back_populates='fiber_ports')

class Cameras(Base):
    __tablename__ = "CAMERAS"

    id= Column(Integer, primary_key=True, index=True)
    type = Column(String(100))
    model = Column(String(120))
    place = Column(String(100))
    Mac = Column(String(100))
    IP = Column(String(100))
    Notes  = Column(String(120))
    show = Column(Boolean)
    Date = Column(String(100))


class Telos(Base):
    __tablename__ = "TELEPHONES"

    id= Column(Integer, primary_key=True, index=True)
    type = Column(String(100))
    model = Column(String(120))
    place = Column(String(100))
    Mac = Column(String(100))
    IP = Column(String(100))
    Notes  = Column(String(120))
    show = Column(Boolean)
    Date = Column(String(100))


class Nursing(Base):
    __tablename__ = "NURSING"

    id= Column(Integer, primary_key=True, index=True)
    type = Column(String(100))
    model = Column(String(120))
    place = Column(String(100))
    Mac = Column(String(100))
    IP = Column(String(100))
    Notes  = Column(String(120))
    show = Column(Boolean)
    Date = Column(String(100))


class AccessPoints(Base):
    __tablename__ = "ACCESS_POINTS"

    id= Column(Integer, primary_key=True, index=True)
    type = Column(String(100))
    model = Column(String(120))
    place = Column(String(100))
    Mac = Column(String(100))
    IP = Column(String(100))
    Notes  = Column(String(120))
    show = Column(Boolean)
    Date = Column(String(100))


class Cabinet(Base):
    __tablename__ = "CABINETS"

    id= Column(Integer, primary_key=True, index=True)
    type = Column(String(100))
    model = Column(String(120))
    place = Column(String(100))
    #Mac = Column(String(100))
    #IP = Column(String(100))
    Notes  = Column(String(120))
    show = Column(Boolean)
    Date = Column(String(100))

