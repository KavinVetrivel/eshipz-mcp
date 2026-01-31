import json
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os 

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("eshipz-mcp")

# Constants
API_BASE_URL = os.getenv("API_BASE_URL", "https://app.eshipz.com")
ESHIPZ_API_TRACKING_URL = f"{API_BASE_URL}/api/v2/trackings"
ESHIPZ_TOKEN = os.getenv("ESHIPZ_TOKEN", "")
ESHIPZ_CARRIER_PERFORMANCE_URL = "http://ds.eshipz.com/scoring/carrier-performance/v1/"

# 
async def make_nws_request(tracking_number: str) -> dict[str, Any] | None:
    headers = {
        "Content-Type": "application/json",
        "X-API-TOKEN": ESHIPZ_TOKEN
    }
    payload = json.dumps({"track_id": tracking_number})
    async with httpx.AsyncClient() as client:
        try:
            # Note: Verify if your API expects data=payload or json=payload
            # Standard libraries often prefer json=... to handle serialization automatically
            response = await client.post(ESHIPZ_API_TRACKING_URL, headers=headers, timeout=30.0, data=payload)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

# the api call is made here after the carrier performance mcp tool invokes the make_carrier_performance_request function 
async def make_carrier_performance_request(source_pin: str, destination_pin: str) -> dict[str, Any] | None:
    headers = {
        "Content-Type": "application/json",
        "X-API-TOKEN": ESHIPZ_TOKEN
    }
    payload = json.dumps({
        "source_pin": source_pin,
        "destination_pin": destination_pin
    })
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                ESHIPZ_CARRIER_PERFORMANCE_URL,
                headers=headers,
                timeout=30.0,
                data=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None



def _format_carrier(slug: str) -> str:
    """Format carrier name for display"""
    return slug.upper() if slug else "Unknown Carrier"


def _create_summary(shipment: dict) -> str:
    """Create human-readable summary based on shipment status"""
    
    tracking_num = shipment.get("tracking_number", "Unknown")
    carrier = _format_carrier(shipment.get("slug"))
    status = shipment.get("tag")
    checkpoints = shipment.get("checkpoints", [])
    latest = checkpoints[0] if checkpoints else {}
    
    location = latest.get("city", "")
    remark = latest.get("remark", "")
    delivery_date = shipment.get("delivery_date")
    eta = shipment.get("expected_delivery_date")
    
    # Status-specific formatting
    if status == "Delivered":
        summary = f" Delivered via {carrier}"
        if delivery_date:
            summary += f" on {delivery_date}"
        if location:
            summary += f" at {location}"
        return summary
    
    elif status == "OutForDelivery":
        summary = f" Out for delivery via {carrier}"
        if location:
            summary += f" from {location}"
        return summary
    
    elif status == "InTransit":
        summary = f"In transit via {carrier}"
        if location:
            summary += f", currently in {location}"
        if remark:
            summary += f" - {remark}"
        if eta:
            summary += f"\n   Expected delivery: {eta}"
        return summary
    
    elif status == "Exception":
        summary = f"Exception via {carrier}"
        if location:
            summary += f" at {location}"
        if remark:
            summary += f" - {remark}"
        return summary
    
    elif status == "PickedUp":
        summary = f"Picked up via {carrier}"
        if location:
            summary += f" from {location}"
        return summary
    
    elif status == "InfoReceived":
        return f"Shipment information received by {carrier}"
    
    else:
        summary = f"{status} via {carrier}" if status else f"Tracking {tracking_num} via {carrier}"
        if location and remark:
            summary += f" - {remark} ({location})"
        elif remark:
            summary += f" - {remark}"
        return summary


def _format_carrier_performance(data: dict) -> str:
    """Format carrier performance data into human-readable summary"""
    
    source_pin = data.get("source_pin", "Unknown")
    dest_pin = data.get("destination_pin", "Unknown")
    carriers = data.get("carriers", [])
    
    if not carriers:
        return f"No carrier performance data available for route {source_pin} to {dest_pin}"
    
    # Build summary header
    summary = f"CARRIER PERFORMANCE ANALYSIS\n"
    summary += f"Route: {source_pin} to {dest_pin}\n"
    summary += f"Carriers analyzed: {len(carriers)}\n"
    summary += f"{'-' * 60}\n\n"
    
    # Sort carriers by score (if available) or alphabetically
    sorted_carriers = sorted(
        carriers,
        key=lambda x: x.get("score", 0),
        reverse=True
    )
    
    for idx, carrier in enumerate(sorted_carriers, 1):
        carrier_name = _format_carrier(carrier.get("slug", carrier.get("name", "Unknown")))
        score = carrier.get("score")
        
        summary += f"{idx}. {carrier_name}"
        
        if score is not None:
            # Add rating classification based on score
            if score >= 90:
                rating = "Excellent"
            elif score >= 75:
                rating = "Good"
            elif score >= 60:
                rating = "Fair"
            else:
                rating = "Below Average"
            summary += f"\n   Performance Score: {score}/100 ({rating})"
        
        # Add additional metrics if available
        metrics = []
        if carrier.get("delivery_rate"):
            metrics.append(f"Delivery Rate: {carrier['delivery_rate']}%")
        if carrier.get("on_time_rate"):
            metrics.append(f"On-Time Rate: {carrier['on_time_rate']}%")
        if carrier.get("avg_delivery_days"):
            metrics.append(f"Avg. Delivery Days: {carrier['avg_delivery_days']}")
        if carrier.get("transit_time"):
            metrics.append(f"Transit Time: {carrier['transit_time']} days")
        
        if metrics:
            for metric in metrics:
                summary += f"\n   {metric}"
        
        summary += "\n\n"
    
    # Add recommendation if top carrier is clear winner
    if len(sorted_carriers) > 1 and sorted_carriers[0].get("score"):
        top_carrier = _format_carrier(sorted_carriers[0].get("slug", sorted_carriers[0].get("name")))
        top_score = sorted_carriers[0].get("score", 0)
        second_score = sorted_carriers[1].get("score", 0)
        
        if top_score - second_score >= 10:
            summary += f"{'-' * 60}\n"
            summary += f"RECOMMENDATION: {top_carrier}\n"
            summary += f"Reason: Highest performance score on this route"
    
    return summary


@mcp.tool()
async def get_tracking(tracking_number: str) -> str:
    """Get tracking information for a shipment
    
    Args:
        tracking_number: The tracking number of the shipment (e.g., "ES123456789")
    
    Returns:
        Formatted tracking summary including status, location, and timestamps.
    """
    
    data = await make_nws_request(tracking_number) #invoking the function to perform the api call
    
    if not data:
        return " Tracking information could not be retrieved. Please verify the tracking number."

    try:
        if isinstance(data, list) and len(data) > 0:
            shipment = data[0]
        else:
            return "No shipment data found in the response."

        # Get summary
        summary = _create_summary(shipment)
        
        # Add latest update timestamp if available
        checkpoints = shipment.get("checkpoints", [])
        if checkpoints:
            latest_time = checkpoints[0].get("date", "")
            if latest_time:
                summary += f"\n   Last updated: {latest_time}"
        
        # Add event count
        event_count = len(checkpoints)
        if event_count > 0:
            summary += f"\n   Total events: {event_count}"
        
        return summary

    except Exception as e:
        return f"Error processing tracking data: {str(e)}"
    
    
@mcp.tool()
async def get_carrier_performance(source_pin: str, destination_pin: str) -> str:
    """Get carrier performance analysis for a specific route
    
    Analyzes and compares carrier performance between two locations based on
    historical delivery data, on-time rates, and transit times.
    
    Args:
        source_pin: Source PIN/postal code (e.g., "421302")
        destination_pin: Destination PIN/postal code (e.g., "560102")
        
    Returns:
        Formatted carrier performance comparison with scores and recommendations
        
    Example:
        get_carrier_performance("421302", "560102")
    """
    data = await make_carrier_performance_request(source_pin, destination_pin) # invoking the function to perform the api call
    
    if not data:
        return f" Carrier performance data could not be retrieved for route {source_pin} → {destination_pin}.\n   Please verify the PIN codes and try again."
    
    try:
        summary = _format_carrier_performance(data)
        return summary
    
    except Exception as e:
        return f" Error processing carrier performance data: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport='stdio')