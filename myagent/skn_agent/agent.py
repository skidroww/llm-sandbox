from google.adk.agents import Agent
from geopy.geocoders import Nominatim
import httpx
import pandas as pd
from dotenv import load_dotenv
load_dotenv()


def get_code(company_name: str) -> dict:
    """
    사용자가 회사 이름을 전달하면 해당 회사의 종목 코드를 dict형태로 반환한다.
    """
    df = pd.read_csv(r"C:\Users\playdata2\Desktop\20260312_openapikey\myagent\data_2058_20260323.csv", encoding='cp949')
    return df[df['한글 종목명'].apply(lambda x : x.find(company_name) > -1)].to_json()


def get_weather(city_name : str) -> dict:
    """
    도시 이름을 사용하여 위도, 경도 위치를 알아내고
    그 값을 통해서 현재 날씨 정보를 반환합니다.
    """
    geo = Nominatim(user_agent='weather_app')
    location = geo.geocode(city_name)
    if location:
        lat, lon  = location.latitude, location.longitude
    else:
        raise ValueError(f'{city_name} 위치의 데이터가 없다 ')
   
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    r = httpx.get(url)


    r.raise_for_status()
    return r.json()


def greet_user() -> str:
    return "안녕"


root_agent = Agent(
    name='skn_agent',
    model="gemini-2.5-flash",
    description='자기소개서 완성하는 에이전트',
    instruction='사용자 요청한 내용을 바탕으로 회사 자기소개서를 완성하는 에이전트임',
    tools = [greet_user,get_weather, get_code]
)
