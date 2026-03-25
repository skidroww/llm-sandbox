from google.adk.tools import google_search
from google.adk.agents import Agent




root_agent = Agent(
    name="news",
    model="gemini-2.5-flash",
    instruction="제공된 기업의 주요 뉴스를 요약할 것. 앞으로 전망도 이야기할 것",
    tools=[google_search]
)
