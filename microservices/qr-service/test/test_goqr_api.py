from fastapi import FastAPI, HTTPException
import httpx
import uvicorn
from pydantic import BaseModel
from typing import Optional
import base64

app = FastAPI(title="GoQR API Test Server")

# Base URL for GoQR API
GOQR_API_BASE_URL = "https://api.qrserver.com/v1"

class QRGenerateRequest(BaseModel):
    data: str
    size: Optional[str] = "200x200"
    format: Optional[str] = "png"

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "goqr-test-server"}

@app.post("/test/generate")
async def test_generate_qr(request: QRGenerateRequest):
    """
    Test endpoint to generate QR code using GoQR API
    """
    try:
        params = {
            "data": request.data,
            "size": request.size,
            "format": request.format
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GOQR_API_BASE_URL}/create-qr-code/",
                params=params
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to generate QR code"
                )
            
            # Convert the image to base64 for easy viewing
            base64_image = base64.b64encode(response.content).decode()
            
            return {
                "status": "success",
                "message": "QR code generated successfully",
                "image_base64": f"data:image/{request.format};base64,{base64_image}"
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating QR code: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100) 