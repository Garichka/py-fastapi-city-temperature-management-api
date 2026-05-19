from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import httpx
import asyncio
import random
from typing import List, Optional
from city_temp_app import models, schemas, database

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="City Temperature API")


@app.post("/cities", response_model=schemas.City, status_code=201)
def create_city(city: schemas.CityCreate, db: Session = Depends(database.get_db)):
    db_city = models.City(name=city.name, additional_info=city.additional_info)
    db.add(db_city)
    db.commit()
    db.refresh(db_city)
    return db_city


@app.get("/cities", response_model=List[schemas.City])
def read_cities(db: Session = Depends(database.get_db)):
    return db.query(models.City).all()


@app.get("/cities/{city_id}", response_model=schemas.City)
def read_city(city_id: int, db: Session = Depends(database.get_db)):
    city = db.query(models.City).filter(models.City.id == city_id).first()
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    return city


@app.delete("/cities/{city_id}")
def delete_city(city_id: int, db: Session = Depends(database.get_db)):
    city = db.query(models.City).filter(models.City.id == city_id).first()
    if not city:
        raise HTTPException(status_code=404, detail="City not found")
    db.delete(city)
    db.commit()
    return {"message": f"City {city_id} deleted successfully"}


async def fetch_weather(city_name: str):
    await asyncio.sleep(0.1)
    return round(random.uniform(15.0, 35.0), 2)


@app.post("/temperatures/update")
async def update_temperatures(db: Session = Depends(database.get_db)):
    cities = db.query(models.City).all()
    if not cities:
        raise HTTPException(status_code=400, detail="No cities in database to update")

    tasks = [fetch_weather(city.name) for city in cities]
    results = await asyncio.gather(*tasks)

    for city, temp in zip(cities, results):
        new_record = models.Temperature(city_id=city.id, temperature=temp)
        db.add(new_record)

    db.commit()
    return {"message": f"Successfully updated temperatures for {len(cities)} cities."}


@app.get("/temperatures", response_model=List[schemas.Temperature])
def get_temperatures(
    city_id: Optional[int] = Query(None), db: Session = Depends(database.get_db)
):
    query = db.query(models.Temperature)
    if city_id:
        query = query.filter(models.Temperature.city_id == city_id)
    return query.all()
