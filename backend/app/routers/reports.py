"""
Reports router for generating and downloading GeoJSON reports.
"""

import uuid
import json
from fpdf import FPDF

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import QueryModel, ChangeResultModel, ImpactStatsModel, ReportModel

router = APIRouter()


@router.get("/{query_id}")
async def get_report(query_id: uuid.UUID, format: str = "geojson", db: AsyncSession = Depends(get_db)):
    """Download a report for a query result."""
    
    result = await db.execute(select(QueryModel).where(QueryModel.id == query_id))
    query = result.scalar_one_or_none()
    
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    if format == "geojson":
        # Construct a GeoJSON FeatureCollection
        features = []
        
        # Add region evidence as features
        if query.evidence:
            for ev in query.evidence:
                if ev.get("type") == "bbox" and ev.get("bbox"):
                    b = ev["bbox"]
                    poly_coords = [[
                        [b["x_min"], b["y_min"]],
                        [b["x_max"], b["y_min"]],
                        [b["x_max"], b["y_max"]],
                        [b["x_min"], b["y_max"]],
                        [b["x_min"], b["y_min"]]
                    ]]
                    
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": poly_coords
                        },
                        "properties": {
                            "label": ev.get("label"),
                            "confidence": ev.get("confidence")
                        }
                    })

        geojson = {
            "type": "FeatureCollection",
            "metadata": {
                "question": query.question,
                "answer": query.answer,
                "confidence": query.confidence
            },
            "features": features
        }
        
        return Response(
            content=json.dumps(geojson, indent=2), 
            media_type="application/geo+json",
            headers={"Content-Disposition": f"attachment; filename=report_{query_id}.geojson"}
        )
        
    elif format == "pdf":
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "SatQuery Analysis Report", 0, 1, "C")
        
        pdf.set_font("Arial", "", 12)
        pdf.ln(10)
        pdf.cell(0, 10, f"Query ID: {query.id}", 0, 1)
        pdf.cell(0, 10, f"Timestamp: {query.created_at}", 0, 1)
        pdf.ln(10)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Question:", 0, 1)
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 10, query.question)
        pdf.ln(5)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "AI Analysis:", 0, 1)
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 10, query.answer)
        pdf.ln(10)
        
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 10, f"Confidence Score: {query.confidence}", 0, 1)
        
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        
        return Response(
            content=pdf_bytes, 
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=report_{query_id}.pdf"}
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid format requested")
