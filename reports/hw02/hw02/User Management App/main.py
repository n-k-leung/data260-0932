from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI(title="Package Management API", version="1.0.0")

# Mount static files directory for serving HTML/CSS/JS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Pydantic models for request/response validation
class Package(BaseModel):
    id: int
    package_name: str
    severity: str=""

class PackageCreate(BaseModel):
    package_name: str
    severity: str=""

class PackageUpdate(BaseModel):
    package_name: str
    severity: str=""

# In-memory package storage
packages: List[Package] = [
    Package(id=1, package_name="nodejs", severity="High"),
    Package(id=2, package_name="python", severity="Low")
]

# Serve the main HTML page
@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

# REST API Endpoints

from fastapi import Response

@app.get("/api/packages/search/{package_name}", response_model=List[Package])
async def search_packages(package_name: str):
    #searching for package name, primary field
    search=package_name.lower().strip()
    if not search:
        return packages
    found_packages=[package for package in packages if search in package.package_name.lower()]
    return found_packages

@app.get("/api/packages", response_model=List[Package])
async def get_packages(response: Response):
    """Get all packages - Returns JSON array of package objects"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return packages

@app.get("/api/packages/{package_id}", response_model=Package)
async def get_package(package_id: int):
    """Get a specific package by ID"""
    package = next((package for package in packages if package.id == package_id), None)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    return package

@app.post("/api/packages", response_model=Package, status_code=201)
async def create_package(package_data: PackageCreate):
    """Create a new package - Accepts JSON with 'package_name' field"""
    if not package_data.package_name.strip():
        raise HTTPException(status_code=400, detail="Package package_name is required")
    
    # Generate new ID
    new_id = max([package.id for package in packages], default=0) + 1
    #add new record for primary and secondary field
    new_package = Package(id=new_id, package_name=package_data.package_name, severity=package_data.severity)
    packages.append(new_package)
    
    print(f"Created package: {new_package}")
    return new_package

@app.put("/api/packages/{package_id}", response_model=Package)
async def update_package(package_id: int, package_data: PackageUpdate):
    """Update an existing package - Accepts JSON with 'package_name' field"""
    package = next((package for package in packages if package.id == package_id), None)
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    if not package_data.package_name.strip():
        raise HTTPException(status_code=400, detail="Package package_name is required")
    #update record id 1 with primary and secondary field values
    package.package_name = package_data.package_name
    package.severity = package_data.severity
    print(f"Updated package: {package}")
    return package

@app.delete("/api/packages/{package_id}", status_code=204)
async def delete_package(package_id: int):
    """Delete a package by ID"""
    global packages
    package_index = next((index for index, package in enumerate(packages) if package.id == package_id), None)
    
    if package_index is None:
        raise HTTPException(status_code=404, detail="Package not found")
    
    deleted_package = packages.pop(package_index)
    print(f"Deleted package: {deleted_package}")
    return None

import webbrowser

# Start the server
if __name__ == "__main__":
    # Open the browser automatically
    webbrowser.open("http://localhost:8032")
    uvicorn.run(app, host="0.0.0.0", port=8032)
