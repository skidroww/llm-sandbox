from google.ㅂ  adk.agents import Agent
from dotenv import load_dotenv
from geopy.geocoders import Nominatim
import httpx

def get_weather(city_name :str) ->dict:
    geo = Nominatim(user_agent='weather_app')
    location = geo.geocode(city_name)

    if not location:
        return {"error": "위치를 찾을 수 없음"}
    
    lat = location.latitude
    lng = location.longitude
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current_weather=true"
    try:
        r = httpx.get(url, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def greet_user() -> str:
    return "안녕"

root_agent = Agent(
    name='skn_agent',
    model="gemini-2.5-flash",
    description='테스트',
    instruction='사용자에게 친한 친구처럼 인사해',
    tools = [greet_user,get_weather]
)


