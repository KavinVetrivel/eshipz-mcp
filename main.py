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
ESHIPZ_CARRIER_PERFORMANCE_URL = "https://ds.eshipz.com/performance_score/cps_scores/v2/"

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
        "sender_postal_code": int(source_pin),
        "tracking_postal_code": int(destination_pin)
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
        except Exception as e:
            print(f"Error in carrier performance request: {str(e)}")
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
    
    # Extract data from API response structure
    detail = data.get("detail", {})
    status = detail.get("status", "")
    
    if status != "SUCCESS":
        return f"API returned non-success status: {status}"
    
    route_data_list = detail.get("data", [])
    
    if not route_data_list:
        return "No carrier performance data available"
    
    # Get first route data (typically there's only one)
    route_data = route_data_list[0]
    
    source_pin = int(route_data.get("sourcepin", 0))
    dest_pin = int(route_data.get("trackingpin", 0))
    
    carrier_slugs = route_data.get("slug_cps_ordered", [])
    delivery_scores = route_data.get("delivery_scores", [])
    pickup_scores = route_data.get("pickup_scores", [])
    rto_scores = route_data.get("rto_scores", [])
    overall_scores = route_data.get("overall_scores", [])
    
    if not carrier_slugs:
        return f"No carriers found for route {source_pin} to {dest_pin}"
    
    # Build summary header
    summary = f"CARRIER PERFORMANCE ANALYSIS\n"
    summary += f"Route: {source_pin} to {dest_pin}\n"
    summary += f"Carriers analyzed: {len(carrier_slugs)}\n"
    summary += f"{'-' * 60}\n\n"
    
    # Create carrier data with scores
    carriers_with_scores = []
    for i, slug in enumerate(carrier_slugs):
        carrier_data = {
            "slug": slug,
            "overall_score": overall_scores[i] if i < len(overall_scores) else None,
            "delivery_score": delivery_scores[i] if i < len(delivery_scores) else None,
            "pickup_score": pickup_scores[i] if i < len(pickup_scores) else None,
            "rto_score": rto_scores[i] if i < len(rto_scores) else None
        }
        carriers_with_scores.append(carrier_data)
    
    # Sort by overall score (descending)
    carriers_with_scores.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    
    for idx, carrier in enumerate(carriers_with_scores, 1):
        carrier_name = _format_carrier(carrier["slug"])
        overall = carrier.get("overall_score")
        
        summary += f"{idx}. {carrier_name}"
        
        if overall is not None:
            # Convert 0-5 scale to 0-100 for display
            score_100 = overall * 20
            if score_100 >= 80:
                rating = "Excellent"
            elif score_100 >= 60:
                rating = "Good"
            elif score_100 >= 40:
                rating = "Fair"
            else:
                rating = "Below Average"
            summary += f"\n   Overall Score: {overall:.1f}/5.0 ({score_100:.0f}/100 - {rating})"
        
        # Add detailed scores
        metrics = []
        if carrier.get("delivery_score") is not None:
            metrics.append(f"Delivery Score: {carrier['delivery_score']:.1f}/5.0")
        if carrier.get("pickup_score") is not None:
            metrics.append(f"Pickup Score: {carrier['pickup_score']:.1f}/5.0")
        if carrier.get("rto_score") is not None:
            metrics.append(f"RTO Score: {carrier['rto_score']:.1f}/5.0")
        
        if metrics:
            for metric in metrics:
                summary += f"\n   {metric}"
        
        summary += "\n\n"
    
    # Add recommendation if top carrier is clear winner
    if len(carriers_with_scores) > 1:
        top_carrier = carriers_with_scores[0]
        second_carrier = carriers_with_scores[1]
        
        top_score = top_carrier.get("overall_score", 0)
        second_score = second_carrier.get("overall_score", 0)
        
        if top_score and second_score and (top_score - second_score) >= 0.5:
            summary += f"{'-' * 60}\n"
            summary += f"RECOMMENDATION: {_format_carrier(top_carrier['slug'])}\n"
            summary += f"Reason: Highest overall performance score on this route"
    
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