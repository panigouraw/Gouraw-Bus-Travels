from database import Base, engine
import models  # important: loads all the table classes

Base.metadata.create_all(bind=engine)
print("All tables created successfully")