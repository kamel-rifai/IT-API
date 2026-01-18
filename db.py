from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


URL_DATABASE = "mysql+pymysql://root:Admin.RJ555@192.168.88.100:3306/IT"

engine = create_engine(URL_DATABASE)

session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


